"""Módulo de persistência SQLite para o briefing semanal da Hipótese Capital.

Gerencia o banco de dados local que armazena snapshots de cada execução,
permitindo versionamento temporal e consulta a dados históricos no dashboard.
"""

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_execucao DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_ativos INTEGER DEFAULT 0,
    ativos_sucesso INTEGER DEFAULT 0,
    ativos_erro INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ativos_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execucao_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    nome_empresa TEXT NOT NULL,
    cotacao TEXT,
    classificacao TEXT,
    indicadores JSON,
    noticias JSON,
    analise JSON,
    FOREIGN KEY (execucao_id) REFERENCES execucoes(id)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_ticker ON ativos_snapshot(ticker);
CREATE INDEX IF NOT EXISTS idx_snapshot_execucao ON ativos_snapshot(execucao_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshot_unique ON ativos_snapshot(execucao_id, ticker);
"""


# ─── Funções de escrita ────────────────────────────────────────────────────────


def inicializar_banco(db_path: str = "data/briefing.db") -> None:
    """Cria as tabelas e índices se não existirem.

    Args:
        db_path: Caminho para o arquivo do banco SQLite.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SCHEMA)
    logger.info("Banco inicializado: %s", db_path)


def criar_execucao(db_path: str, data_execucao: str, total_ativos: int) -> int:
    """Cria um registro de execução e retorna o execucao_id gerado.

    Args:
        db_path: Caminho para o banco SQLite.
        data_execucao: Data no formato YYYY-MM-DD.
        total_ativos: Total de ativos a serem processados nesta execução.

    Returns:
        ID da execução recém-criada.
    """
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO execucoes (data_execucao, total_ativos) VALUES (?, ?)",
            (data_execucao, total_ativos),
        )
        execucao_id = cur.lastrowid
    logger.info("Execução criada: id=%d data=%s ativos=%d", execucao_id, data_execucao, total_ativos)
    return execucao_id


def salvar_snapshot(
    db_path: str,
    execucao_id: int,
    ticker: str,
    nome_empresa: str,
    cotacao: str,
    indicadores: dict,
    noticias: list,
    analise: dict,
    classificacao: str,
) -> None:
    """Salva o snapshot de um ativo para uma execução.

    Usa INSERT OR REPLACE para garantir unicidade por (execucao_id, ticker).

    Args:
        db_path: Caminho para o banco SQLite.
        execucao_id: ID da execução pai.
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa.
        cotacao: Cotação atual como string (ex: "62,69").
        indicadores: Dict completo de indicadores fundamentalistas.
        noticias: Lista de notícias coletadas.
        analise: Dict completo da análise LLM.
        classificacao: Label do semáforo ("atrativo", "cautela" ou "neutro").
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ativos_snapshot
                (execucao_id, ticker, nome_empresa, cotacao, classificacao,
                 indicadores, noticias, analise)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(execucao_id, ticker) DO UPDATE SET
                nome_empresa   = excluded.nome_empresa,
                cotacao        = excluded.cotacao,
                classificacao  = excluded.classificacao,
                indicadores    = excluded.indicadores,
                noticias       = excluded.noticias,
                analise        = excluded.analise
            """,
            (
                execucao_id,
                ticker,
                nome_empresa,
                cotacao,
                classificacao,
                json.dumps(indicadores, ensure_ascii=False),
                json.dumps(noticias, ensure_ascii=False),
                json.dumps(analise, ensure_ascii=False),
            ),
        )
    logger.debug("[%s] snapshot salvo (execucao_id=%d)", ticker, execucao_id)


def finalizar_execucao(db_path: str, execucao_id: int, ativos_sucesso: int, ativos_erro: int) -> None:
    """Atualiza os contadores de sucesso e erro da execução.

    Args:
        db_path: Caminho para o banco SQLite.
        execucao_id: ID da execução a finalizar.
        ativos_sucesso: Quantidade de ativos processados com sucesso.
        ativos_erro: Quantidade de ativos que falharam.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE execucoes SET ativos_sucesso = ?, ativos_erro = ? WHERE id = ?",
            (ativos_sucesso, ativos_erro, execucao_id),
        )
    logger.info("Execução %d finalizada: %d sucesso, %d erro", execucao_id, ativos_sucesso, ativos_erro)


# ─── Funções de leitura ────────────────────────────────────────────────────────


def buscar_ultima_execucao(db_path: str) -> dict | None:
    """Retorna a execução mais recente do banco.

    Args:
        db_path: Caminho para o banco SQLite.

    Returns:
        Dict com os campos da execução, ou None se não houver nenhuma.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM execucoes ORDER BY data_execucao DESC, id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def buscar_execucao_por_data(db_path: str, data: str) -> dict | None:
    """Retorna a execução mais recente de uma data específica.

    Args:
        db_path: Caminho para o banco SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Dict com os campos da execução, ou None se não encontrada.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM execucoes WHERE data_execucao = ? ORDER BY id DESC LIMIT 1",
            (data,),
        ).fetchone()
    return dict(row) if row else None


def buscar_snapshots(db_path: str, execucao_id: int) -> list[dict]:
    """Retorna todos os snapshots de uma execução com os campos JSON já parseados.

    Args:
        db_path: Caminho para o banco SQLite.
        execucao_id: ID da execução.

    Returns:
        Lista de dicts com indicadores, noticias e analise já desserializados.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM ativos_snapshot WHERE execucao_id = ? ORDER BY ticker",
            (execucao_id,),
        ).fetchall()

    resultado = []
    for row in rows:
        item = dict(row)
        for campo in ("indicadores", "noticias", "analise"):
            if item.get(campo):
                try:
                    item[campo] = json.loads(item[campo])
                except (json.JSONDecodeError, TypeError):
                    item[campo] = {} if campo != "noticias" else []
        resultado.append(item)
    return resultado


def listar_tickers_por_data(db_path: str, data: str) -> list[tuple[str, str]]:
    """Lista todos os tickers disponíveis em uma data com seus nomes.

    Args:
        db_path: Caminho para o banco SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Lista de tuplas (ticker, nome_empresa) ordenada por ticker.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            WITH latest AS (
                SELECT s.ticker, s.nome_empresa, MAX(s.id) AS max_id
                FROM ativos_snapshot s
                JOIN execucoes e ON e.id = s.execucao_id
                WHERE e.data_execucao = ?
                GROUP BY s.ticker
            )
            SELECT ticker, nome_empresa FROM latest ORDER BY ticker
            """,
            (data,),
        ).fetchall()
    return [(row["ticker"], row["nome_empresa"]) for row in rows]


def buscar_snapshots_por_data(db_path: str, data: str) -> list[dict]:
    """Retorna o snapshot mais recente de cada ticker em todas as execuções de uma data.

    Se o mesmo ticker aparece em múltiplas execuções do dia, retorna apenas
    o snapshot da execução mais recente. Tickers que só existem em execuções
    anteriores do dia também são incluídos.

    Args:
        db_path: Caminho para o banco SQLite.
        data: Data no formato YYYY-MM-DD.

    Returns:
        Lista de dicts com indicadores, noticias e analise já desserializados.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            WITH latest AS (
                SELECT s.ticker, MAX(s.id) AS max_id
                FROM ativos_snapshot s
                JOIN execucoes e ON e.id = s.execucao_id
                WHERE e.data_execucao = ?
                GROUP BY s.ticker
            )
            SELECT s.* FROM ativos_snapshot s
            JOIN latest l ON s.id = l.max_id
            ORDER BY s.ticker
            """,
            (data,),
        ).fetchall()

    resultado = []
    for row in rows:
        item = dict(row)
        for campo in ("indicadores", "noticias", "analise"):
            if item.get(campo):
                try:
                    item[campo] = json.loads(item[campo])
                except (json.JSONDecodeError, TypeError):
                    item[campo] = {} if campo != "noticias" else []
        resultado.append(item)
    return resultado


def buscar_historico_ticker(db_path: str, ticker: str, limite: int = 30) -> list[dict]:
    """Retorna os últimos N snapshots de um ticker, ordenados por data decrescente.

    Extrai P/L e Div. Yield dos indicadores armazenados em JSON para uso
    na timeline histórica do dashboard.

    Args:
        db_path: Caminho para o banco SQLite.
        ticker: Código do ativo (ex: "PRIO3").
        limite: Número máximo de registros a retornar.

    Returns:
        Lista de dicts com: data, cotacao, classificacao, pl, dy.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.cotacao, s.classificacao, s.indicadores,
                   e.data_execucao
            FROM ativos_snapshot s
            JOIN execucoes e ON e.id = s.execucao_id
            WHERE s.ticker = ?
            ORDER BY e.data_execucao DESC, e.id DESC
            LIMIT ?
            """,
            (ticker, limite),
        ).fetchall()

    resultado = []
    datas_vistas: set[str] = set()
    for row in rows:
        data = row["data_execucao"]
        if data in datas_vistas:
            continue
        datas_vistas.add(data)

        indicadores = {}
        if row["indicadores"]:
            try:
                indicadores = json.loads(row["indicadores"])
            except (json.JSONDecodeError, TypeError):
                pass

        pl = _extrair_indicador(indicadores, ["P/L"])
        dy = _extrair_indicador(indicadores, ["Div. Yield", "Div.Yield", "DY", "Dividend Yield"])

        resultado.append({
            "data": data,
            "cotacao": row["cotacao"] or "—",
            "classificacao": row["classificacao"] or "neutro",
            "pl": pl,
            "dy": dy,
        })
    return resultado


def buscar_historico_completo_ticker(db_path: str, ticker: str, limite: int = 30) -> list[dict]:
    """Retorna os últimos N snapshots completos de um ticker com indicadores e análise.

    Diferente de buscar_historico_ticker, retorna os dicts completos de indicadores
    e analise desserializados, para uso no explorador histórico do dashboard.

    Args:
        db_path: Caminho para o banco SQLite.
        ticker: Código do ativo (ex: "PRIO3").
        limite: Número máximo de registros a retornar.

    Returns:
        Lista de dicts com: data, cotacao, classificacao, pl, dy, indicadores, analise.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.cotacao, s.classificacao, s.indicadores, s.analise,
                   e.data_execucao
            FROM ativos_snapshot s
            JOIN execucoes e ON e.id = s.execucao_id
            WHERE s.ticker = ?
            ORDER BY e.data_execucao DESC, e.id DESC
            LIMIT ?
            """,
            (ticker, limite),
        ).fetchall()

    resultado = []
    datas_vistas: set[str] = set()
    for row in rows:
        data = row["data_execucao"]
        if data in datas_vistas:
            continue
        datas_vistas.add(data)

        indicadores: dict = {}
        analise: dict = {}
        if row["indicadores"]:
            try:
                indicadores = json.loads(row["indicadores"])
            except (json.JSONDecodeError, TypeError):
                pass
        if row["analise"]:
            try:
                analise = json.loads(row["analise"])
            except (json.JSONDecodeError, TypeError):
                pass

        pl = _extrair_indicador(indicadores, ["P/L"])
        dy = _extrair_indicador(indicadores, ["Div. Yield", "Div.Yield", "DY", "Dividend Yield"])

        resultado.append({
            "data": data,
            "cotacao": row["cotacao"] or "—",
            "classificacao": row["classificacao"] or "neutro",
            "pl": pl,
            "dy": dy,
            "indicadores": indicadores,
            "analise": analise,
        })
    return resultado


def listar_datas_execucao(db_path: str, limite: int = 30) -> list[str]:
    """Lista as últimas N datas de execução disponíveis no banco.

    Args:
        db_path: Caminho para o banco SQLite.
        limite: Número máximo de datas a retornar.

    Returns:
        Lista de datas no formato YYYY-MM-DD, ordenadas da mais recente para a mais antiga.
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT data_execucao FROM execucoes ORDER BY data_execucao DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [row[0] for row in rows]


# ─── Utilitários internos ──────────────────────────────────────────────────────


def _extrair_indicador(indicadores: dict, chaves: list[str]) -> str:
    """Busca o valor de um indicador tentando múltiplas chaves alternativas.

    Args:
        indicadores: Dict de indicadores fundamentalistas.
        chaves: Lista de chaves a tentar, em ordem de preferência.

    Returns:
        Valor encontrado como string, ou "—" se nenhuma chave corresponder.
    """
    for chave in chaves:
        valor = indicadores.get(chave)
        if valor is not None and str(valor).strip():
            return str(valor)
    return "—"
