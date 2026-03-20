"""Orquestrador principal do briefing semanal da Hipótese Capital."""

import argparse
import json
import logging
import os
import re
import sys
import threading
import time
import webbrowser
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Garante que src/ seja encontrado quando executado da raiz
sys.path.insert(0, str(Path(__file__).parent))

import database
from analise_llm import gerar_analise
from coleta_indicadores import coletar_indicadores
from coleta_noticias import coletar_noticias
from gera_dashboard import gerar_dashboard

# ─── Configuração de logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Caminhos ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ATIVOS_PATH = ROOT / "data" / "ativos.txt"
OUTPUT_DIR = ROOT / "data" / "output"
TEMPLATE_PATH = ROOT / "dashboard" / "template.html"
DASHBOARD_OUTPUT = ROOT / "dashboard" / "output" / "index.html"
DB_PATH = str(ROOT / "data" / "briefing.db")


def carregar_ativos(caminho: Path) -> list[tuple[str, str]]:
    """Lê o arquivo de ativos e retorna lista de (ticker, nome_empresa).

    Args:
        caminho: Caminho para o arquivo ativos.txt.

    Returns:
        Lista de tuplas (ticker, nome_empresa).
    """
    ativos = []
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or "|" not in linha:
                continue
            ticker, nome = linha.split("|", 1)
            ativos.append((ticker.strip(), nome.strip()))
    return ativos


_TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")
_TIMEOUT_INATIVIDADE = 60  # segundos


def _input_timeout(prompt: str, timeout: float) -> str | None:
    """Lê input do terminal com timeout. Retorna None se o tempo esgotar."""
    resultado: list[str | None] = [None]
    evento = threading.Event()

    def _ler() -> None:
        resultado[0] = input(prompt)
        evento.set()

    t = threading.Thread(target=_ler, daemon=True)
    t.start()
    evento.wait(timeout)
    return resultado[0]


def _validar_ticker(ticker: str) -> str | None:
    """Retorna mensagem de erro ou None se válido."""
    t = ticker.strip().upper()
    if not t:
        return "Ticker não pode ser vazio."
    if not _TICKER_RE.match(t):
        return f"'{t}' não é um ticker válido. Use o formato XXXX3 (4 letras + 1 ou 2 dígitos)."
    return None


def selecionar_ativos(
    ativos_base: list[tuple[str, str]],
    caminho: Path,
    hoje: str | None = None,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Loop interativo para adicionar/remover ativos antes de gerar o relatório.

    Na confirmação (G), verifica quais ativos já foram processados hoje e
    pergunta se deve reprocessar todos ou apenas os novos.

    Args:
        ativos_base: Lista inicial carregada de ativos.txt.
        caminho: Caminho para ativos.txt (será atualizado ao confirmar).
        hoje: Data atual (YYYY-MM-DD) para verificar execuções do dia.

    Returns:
        Tupla (ativos_a_processar, tickers_do_banco):
        - ativos_a_processar: (ticker, nome) que devem ser coletados/analisados
        - tickers_do_banco: tickers cujos dados devem ser carregados do banco
    """
    ativos: list[tuple[str, str]] = list(ativos_base)

    while True:
        print("\n════════════════════════════════════════════════════")
        print("  ATIVOS NA LISTA ATUAL:")
        if ativos:
            for i, (t, n) in enumerate(ativos, 1):
                print(f"    {i:2}. {t} | {n}")
        else:
            print("    (lista vazia)")
        print("════════════════════════════════════════════════════")
        print("  A  → adicionar um ativo à lista     (pedirá ticker e nome)")
        print("  R  → remover um ativo da lista      (pedirá ticker ou nome)")
        print("  G  → gerar o relatório com esta lista")
        print(f"\n  Após {_TIMEOUT_INATIVIDADE}s sem input, o relatório será gerado automaticamente.")
        print("════════════════════════════════════════════════════")
        cmd_raw = _input_timeout("\nComando (A / R / G): ", _TIMEOUT_INATIVIDADE)

        if cmd_raw is None:
            if not ativos:
                print("\n  Tempo esgotado, mas a lista está vazia. Adicione pelo menos um ativo.")
                continue
            print("\n  Tempo esgotado. Gerando relatório com a lista atual...")
            with open(caminho, "w", encoding="utf-8") as f:
                f.write("\n".join(f"{t}|{n}" for t, n in ativos) + "\n")
            return _confirmar_reprocessamento(ativos, hoje)

        cmd = cmd_raw.strip().upper()

        if cmd == "A":
            ticker_raw = input("  Digite o ticker a ser adicionado (ou Z para cancelar): ").strip().upper()
            if ticker_raw == "Z":
                continue
            erro = _validar_ticker(ticker_raw)
            if erro:
                print(f"  ✗ {erro}")
                continue
            if any(t == ticker_raw for t, _ in ativos):
                print(f"  ✗ '{ticker_raw}' já está na lista.")
                continue
            nome = input("  Digite o nome da empresa a ser adicionada (ou Z para cancelar): ").strip()
            if nome.upper() == "Z":
                continue
            if not nome:
                print("  ✗ Nome da empresa não pode ser vazio.")
                continue
            ativos.append((ticker_raw, nome))
            print(f"  ✓ {ticker_raw} | {nome} adicionado.")

        elif cmd == "R":
            termo = input("  Digite o ticker ou nome da empresa a ser removida (ou Z para cancelar): ").strip().upper()
            if termo == "Z":
                continue
            if not termo:
                print("  ✗ Digite um ticker ou nome para remover.")
                continue
            antes = len(ativos)
            ativos = [
                (t, n) for t, n in ativos
                if t != termo and n.upper() != termo
            ]
            if len(ativos) == antes:
                print(f"  ✗ '{termo}' não encontrado na lista.")
            else:
                print(f"  ✓ Ativo removido.")

        elif cmd == "G":
            if not ativos:
                print("  ✗ A lista está vazia. Adicione pelo menos um ativo.")
                continue
            # Persiste a lista atualizada
            with open(caminho, "w", encoding="utf-8") as f:
                f.write("\n".join(f"{t}|{n}" for t, n in ativos) + "\n")
            return _confirmar_reprocessamento(ativos, hoje)

        else:
            print(f"  ✗ Comando '{cmd}' inválido. Use A, R ou G.")


def _confirmar_reprocessamento(
    ativos: list[tuple[str, str]],
    hoje: str | None,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Verifica quais ativos já foram processados hoje e pergunta o que fazer.

    Args:
        ativos: Lista completa de (ticker, nome) selecionados.
        hoje: Data atual (YYYY-MM-DD).

    Returns:
        Tupla (ativos_a_processar, tickers_do_banco).
    """
    if not hoje:
        return ativos, []

    ja_processados = database.listar_tickers_por_data(DB_PATH, hoje)
    ja_set = {t for t, _ in ja_processados}

    novos = [(t, n) for t, n in ativos if t not in ja_set]
    existentes = [(t, n) for t, n in ativos if t in ja_set]

    if not existentes:
        # Nenhum foi processado hoje — processar todos
        return ativos, []

    print("\n════════════════════════════════════════════════════")
    print(f"  {len(existentes)} ativo(s) já processados hoje:")
    for t, n in existentes:
        print(f"    • {t} | {n}")
    if novos:
        print(f"\n  {len(novos)} ativo(s) novos (ainda não processados):")
        for t, n in novos:
            print(f"    • {t} | {n}")
    else:
        print("\n  Nenhum ativo novo na lista.")
    print("════════════════════════════════════════════════════")
    print("  T  → reprocessar TODOS (recoleta e reanálise inclusive dos já feitos)")
    print("  N  → processar somente os NOVOS (usa dados salvos para os demais)")
    print(f"\n  Após {_TIMEOUT_INATIVIDADE}s, processa somente os novos.")
    print("════════════════════════════════════════════════════")

    cmd_raw = _input_timeout("\nComando (T / N): ", _TIMEOUT_INATIVIDADE)
    cmd = cmd_raw.strip().upper() if cmd_raw else "N"
    if cmd_raw is None:
        print("  Tempo esgotado. Processando somente os novos...")

    if cmd == "T":
        return ativos, []
    else:
        tickers_do_banco = [t for t, _ in existentes]
        return novos, tickers_do_banco


def processar_ativo(ticker: str, nome_empresa: str) -> dict:
    """Executa o pipeline completo de coleta e análise para um ativo.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dict com indicadores, noticias e analise do ativo.
    """
    indicadores = coletar_indicadores(ticker, nome_empresa)
    noticias = coletar_noticias(ticker, nome_empresa)
    analise = gerar_analise(ticker, nome_empresa, indicadores, noticias)

    # Injeta sentimento, justificativa e relevância nas notícias por índice.
    # Também enriquece analise.noticias_classificadas com link/fonte/data_publicacao
    # dos dados brutos para que o dashboard use noticias_classificadas como fonte única.
    classificadas = analise.get("noticias_classificadas", [])
    for i, noticia in enumerate(noticias):
        match = classificadas[i] if i < len(classificadas) else {}
        noticia["sentimento"] = match.get("sentimento", "neutro")
        noticia["justificativa"] = match.get("justificativa", "")
        noticia["relevante"] = match.get("relevante", True)
        if i < len(classificadas):
            fonte = noticia.get("fonte", "")
            classificadas[i]["link"] = noticia.get("link", "")
            classificadas[i]["fonte"] = fonte
            classificadas[i]["data_publicacao"] = noticia.get("data_publicacao", "")
            # Remove "(Fonte)" duplicado que o LLM às vezes inclui no título
            if fonte:
                titulo = classificadas[i].get("titulo", "")
                classificadas[i]["titulo"] = titulo.replace(f"({fonte})", "").strip()

    # Remove notícias marcadas como não relacionadas ao ativo
    noticias_filtradas = [n for n in noticias if n.get("relevante", True)]
    removidas = len(noticias) - len(noticias_filtradas)
    if removidas:
        logger.info("[%s] %d notícia(s) removida(s) por irrelevância", ticker, removidas)

    return {
        "ticker": ticker,
        "nome_empresa": nome_empresa,
        "indicadores": indicadores,
        "noticias": noticias_filtradas,
        "analise": analise,
    }


def _args() -> argparse.Namespace:
    """Processa os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Briefing semanal da Hipótese Capital",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python src/main.py                        # execução completa\n"
            "  python src/main.py --apenas-dashboard     # regenera dashboard da última execução\n"
            "  python src/main.py --data 2026-03-14      # dashboard de uma data específica\n"
        ),
    )
    parser.add_argument(
        "--apenas-dashboard",
        action="store_true",
        help="Regenera o dashboard a partir da última execução no banco, sem coletar dados novos.",
    )
    parser.add_argument(
        "--data",
        metavar="YYYY-MM-DD",
        help="Gera o dashboard para uma data específica do banco.",
    )
    return parser.parse_args()


def _selecionar_ativos_dashboard(
    ativos_txt: list[tuple[str, str]],
    disponiveis: list[tuple[str, str]],
) -> list[str]:
    """Menu interativo para selecionar quais ativos do banco incluir no dashboard.

    Começa com os ativos de ativos.txt que existem no banco. O usuário pode
    adicionar ativos extras disponíveis no banco ou remover da seleção.

    Args:
        ativos_txt: Ativos carregados de ativos.txt (ticker, nome).
        disponiveis: Ativos disponíveis no banco para a data (ticker, nome).

    Returns:
        Lista de tickers selecionados.
    """
    disp_map = {t: n for t, n in disponiveis}
    txt_set = {t for t, _ in ativos_txt}

    # Seleção inicial: ativos.txt ∩ disponíveis no banco
    selecionados = [t for t in disp_map if t in txt_set]
    # Manter a ordem do ativos.txt para os que já estão, depois os extras
    selecionados.sort(key=lambda t: (t not in txt_set, t))

    while True:
        fora = [(t, n) for t, n in disponiveis if t not in selecionados]

        print("\n════════════════════════════════════════════════════")
        print("  ATIVOS SELECIONADOS PARA O DASHBOARD:")
        if selecionados:
            for i, t in enumerate(selecionados, 1):
                print(f"    {i:2}. {t} | {disp_map[t]}")
        else:
            print("    (nenhum)")
        if fora:
            print(f"\n  DISPONÍVEIS NO BANCO (não selecionados): {', '.join(t for t, _ in fora)}")
        print("════════════════════════════════════════════════════")
        print("  A  → adicionar um ativo disponível no banco")
        print("  R  → remover um ativo da seleção")
        print("  T  → adicionar TODOS os disponíveis")
        print("  G  → gerar o dashboard com esta seleção")
        print(f"\n  Após {_TIMEOUT_INATIVIDADE}s sem input, gera automaticamente.")
        print("════════════════════════════════════════════════════")
        cmd_raw = _input_timeout("\nComando (A / R / T / G): ", _TIMEOUT_INATIVIDADE)

        if cmd_raw is None:
            if not selecionados:
                print("\n  Tempo esgotado, mas a seleção está vazia. Adicione pelo menos um ativo.")
                continue
            print("\n  Tempo esgotado. Gerando dashboard com a seleção atual...")
            return selecionados

        cmd = cmd_raw.strip().upper()

        if cmd == "A":
            if not fora:
                print("  ✗ Todos os ativos disponíveis já estão selecionados.")
                continue
            print("  Disponíveis para adicionar:")
            for i, (t, n) in enumerate(fora, 1):
                print(f"    {i:2}. {t} | {n}")
            escolha = input("  Digite o ticker ou número (ou Z para cancelar): ").strip().upper()
            if escolha == "Z":
                continue
            # Aceita número ou ticker
            ticker_add = None
            if escolha.isdigit():
                idx = int(escolha) - 1
                if 0 <= idx < len(fora):
                    ticker_add = fora[idx][0]
            else:
                ticker_add = escolha if escolha in disp_map and escolha not in selecionados else None
            if ticker_add:
                selecionados.append(ticker_add)
                print(f"  ✓ {ticker_add} adicionado.")
            else:
                print(f"  ✗ '{escolha}' não encontrado nos disponíveis.")

        elif cmd == "R":
            if not selecionados:
                print("  ✗ A seleção já está vazia.")
                continue
            termo = input("  Digite o ticker a remover (ou Z para cancelar): ").strip().upper()
            if termo == "Z":
                continue
            if termo in selecionados:
                selecionados.remove(termo)
                print(f"  ✓ {termo} removido.")
            else:
                print(f"  ✗ '{termo}' não está na seleção.")

        elif cmd == "T":
            selecionados = [t for t, _ in disponiveis]
            print(f"  ✓ Todos os {len(selecionados)} ativos selecionados.")

        elif cmd == "G":
            if not selecionados:
                print("  ✗ A seleção está vazia. Adicione pelo menos um ativo.")
                continue
            return selecionados

        else:
            print(f"  ✗ Comando '{cmd}' inválido. Use A, R, T ou G.")


def _gerar_dashboard_do_banco(data_execucao: str, tickers: list[str] | None = None) -> None:
    """Reconstrói o payload e gera o dashboard com ativos de uma data.

    Agrega os snapshots de TODAS as execuções do dia, mantendo o mais recente
    de cada ticker. Se tickers for fornecido, inclui apenas esses.

    Args:
        data_execucao: Data no formato YYYY-MM-DD.
        tickers: Lista de tickers a incluir. Se None, inclui todos.
    """
    snapshots = database.buscar_snapshots_por_data(DB_PATH, data_execucao)
    if not snapshots:
        logger.error("Nenhum snapshot encontrado para %s", data_execucao)
        sys.exit(1)

    resultados = {}
    for snap in snapshots:
        if tickers and snap["ticker"] not in tickers:
            continue
        resultados[snap["ticker"]] = {
            "ticker": snap["ticker"],
            "nome_empresa": snap["nome_empresa"],
            "indicadores": snap["indicadores"],
            "noticias": snap["noticias"],
            "analise": snap["analise"],
        }

    if not resultados:
        logger.error("Nenhum dos tickers selecionados encontrado nos dados de %s", data_execucao)
        sys.exit(1)

    logger.info("Dashboard com %d ativos de %s", len(resultados), data_execucao)
    payload = {"data_geracao": data_execucao, "ativos": resultados}
    DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gerar_dashboard(payload, str(TEMPLATE_PATH), str(DASHBOARD_OUTPUT), DB_PATH)
    print(f"\n✓ Dashboard gerado em: {DASHBOARD_OUTPUT}")
    webbrowser.open(DASHBOARD_OUTPUT.as_uri())


def main() -> None:
    """Ponto de entrada do orquestrador."""
    load_dotenv()
    args = _args()

    database.inicializar_banco(DB_PATH)

    # ── Modos sem coleta: --apenas-dashboard ou --data ────────────────────
    if args.apenas_dashboard or args.data:
        if args.data:
            data_alvo = args.data
        else:
            execucao = database.buscar_ultima_execucao(DB_PATH)
            if not execucao:
                logger.error("Nenhuma execução encontrada no banco. Rode sem argumentos primeiro.")
                sys.exit(1)
            data_alvo = execucao["data_execucao"]

        disponiveis = database.listar_tickers_por_data(DB_PATH, data_alvo)
        if not disponiveis:
            logger.error("Nenhum ativo encontrado no banco para %s", data_alvo)
            sys.exit(1)

        ativos_txt = carregar_ativos(ATIVOS_PATH)
        tickers = _selecionar_ativos_dashboard(ativos_txt, disponiveis)
        logger.info("Gerando dashboard com %d ativos de %s", len(tickers), data_alvo)
        _gerar_dashboard_do_banco(data_alvo, tickers)
        return

    # ── Execução completa ─────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        logger.error("Nenhuma chave de análise encontrada — configure ANTHROPIC_API_KEY ou OPENAI_API_KEY no .env")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY não encontrada — análise será feita via GPT-4o")
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY não encontrada — GPT-4o desativado (fallback de coleta e enriquecimento GPT-mini indisponíveis)")
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY não encontrada — síntese Gemini desativada")

    ativos_base = carregar_ativos(ATIVOS_PATH)
    hoje = date.today().isoformat()
    ativos, tickers_do_banco = selecionar_ativos(ativos_base, ATIVOS_PATH, hoje)

    if not ativos and not tickers_do_banco:
        logger.error("Nenhum ativo para processar.")
        sys.exit(1)

    # ── Processamento ─────────────────────────────────────────────────────
    logger.info("Iniciando briefing — %d a processar, %d do banco", len(ativos), len(tickers_do_banco))

    execucao_id = database.criar_execucao(DB_PATH, hoje, len(ativos)) if ativos else None

    inicio = time.time()
    resultados = {}
    erros = []

    # Carrega dados do banco para ativos já processados
    if tickers_do_banco:
        snapshots = database.buscar_snapshots_por_data(DB_PATH, hoje)
        for snap in snapshots:
            if snap["ticker"] in tickers_do_banco:
                resultados[snap["ticker"]] = {
                    "ticker": snap["ticker"],
                    "nome_empresa": snap["nome_empresa"],
                    "indicadores": snap["indicadores"],
                    "noticias": snap["noticias"],
                    "analise": snap["analise"],
                }
        logger.info("%d ativo(s) carregados do banco", len(tickers_do_banco))

    # Processa os novos (coleta + análise)
    total = len(ativos)
    for i, (ticker, nome_empresa) in enumerate(ativos, start=1):
        logger.info("[%s] iniciando (%d/%d)", ticker, i, total)
        try:
            resultado = processar_ativo(ticker, nome_empresa)
            resultados[ticker] = resultado

            # Salva snapshot no banco
            analise = resultado.get("analise", {})
            indicadores = resultado.get("indicadores", {})
            cotacao = str(indicadores.get("Cotação", ""))
            classificacao = analise.get("classificacao", {}).get("label", "neutro")
            database.salvar_snapshot(
                db_path=DB_PATH,
                execucao_id=execucao_id,
                ticker=ticker,
                nome_empresa=nome_empresa,
                cotacao=cotacao,
                indicadores=indicadores,
                noticias=resultado.get("noticias", []),
                analise=analise,
                classificacao=classificacao,
            )
        except Exception as e:
            logger.error("[%s] falha: %s", ticker, e)
            erros.append(ticker)

    if execucao_id:
        database.finalizar_execucao(DB_PATH, execucao_id, len(ativos) - len(erros), len(erros))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{hoje}.json"

    payload = {"data_geracao": hoje, "ativos": resultados}

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("JSON salvo: %s", json_path.name)

    gerar_dashboard(payload, str(TEMPLATE_PATH), str(DASHBOARD_OUTPUT), DB_PATH)

    duracao = time.time() - inicio
    processados = len(ativos) - len(erros)
    logger.info(
        "Concluído — %d processados + %d do banco em %.1fs%s",
        processados,
        len(tickers_do_banco),
        duracao,
        f" | erros: {erros}" if erros else "",
    )
    print(f"\n✓ Dashboard gerado em: {DASHBOARD_OUTPUT}")
    webbrowser.open(DASHBOARD_OUTPUT.as_uri())


if __name__ == "__main__":
    main()
