"""Orquestrador principal do briefing semanal da Hipótese Capital."""

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


def selecionar_ativos(ativos_base: list[tuple[str, str]], caminho: Path) -> list[tuple[str, str]]:
    """Loop interativo para adicionar/remover ativos antes de gerar o relatório.

    Args:
        ativos_base: Lista inicial carregada de ativos.txt.

    Returns:
        Lista final de ativos confirmada pelo usuário.
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
        print("  Para modificar a lista acima, digite a letra do comando correspondente e pressione Enter:\n")
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
            return ativos

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
            print("\n  Ativos a processar:")
            for i, (t, n) in enumerate(ativos, 1):
                print(f"    {i:2}. {t} | {n}")
            print(f"\n  (Sem resposta em {_TIMEOUT_INATIVIDADE}s, o relatório será gerado automaticamente.)")
            conf_raw = _input_timeout("\n  Digite S para confirmar e N para cancelar: ", _TIMEOUT_INATIVIDADE)
            confirmacao = conf_raw.strip().upper() if conf_raw is not None else "S"
            if conf_raw is None:
                print("  Tempo esgotado. Gerando relatório automaticamente...")
            if confirmacao == "S":
                # Persiste a lista atualizada no arquivo
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write("\n".join(f"{t}|{n}" for t, n in ativos) + "\n")
                return ativos
            elif confirmacao == "N":
                continue
            else:
                print("  ✗ Digite S para confirmar ou N para cancelar.")

        else:
            print(f"  ✗ Comando '{cmd}' inválido. Use A, R ou G.")


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


def main() -> None:
    """Ponto de entrada do orquestrador."""
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY não encontrada — configure o .env")
        sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY não encontrada — GPT-4o desativado (fallback de coleta e síntese indisponíveis)")
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY não encontrada — síntese Gemini desativada; análise Claude será usada diretamente")

    ativos_base = carregar_ativos(ATIVOS_PATH)
    ativos = selecionar_ativos(ativos_base, ATIVOS_PATH)
    logger.info("Iniciando briefing — %d ativos", len(ativos))

    inicio = time.time()
    resultados = {}
    erros = []

    total = len(ativos)
    for i, (ticker, nome_empresa) in enumerate(ativos, start=1):
        logger.info("[%s] iniciando (%d/%d)", ticker, i, total)
        try:
            resultados[ticker] = processar_ativo(ticker, nome_empresa)
        except Exception as e:
            logger.error("[%s] falha: %s", ticker, e)
            erros.append(ticker)

    hoje = date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{hoje}.json"

    payload = {"data_geracao": hoje, "ativos": resultados}

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("JSON salvo: %s", json_path.name)

    gerar_dashboard(payload, str(TEMPLATE_PATH), str(DASHBOARD_OUTPUT))

    duracao = time.time() - inicio
    ok = len(ativos) - len(erros)
    logger.info(
        "Concluído — %d/%d ativos em %.1fs%s",
        ok,
        len(ativos),
        duracao,
        f" | erros: {erros}" if erros else "",
    )
    print(f"\n✓ Dashboard gerado em: {DASHBOARD_OUTPUT}")
    webbrowser.open(DASHBOARD_OUTPUT.as_uri())


if __name__ == "__main__":
    main()
