"""Orquestrador principal do briefing semanal da Hipótese Capital."""

import json
import logging
import os
import sys
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
DASHBOARD_OUTPUT = ROOT / "dashboard" / "index.html"


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


def processar_ativo(ticker: str, nome_empresa: str) -> dict:
    """Executa o pipeline completo de coleta e análise para um ativo.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dict com indicadores, noticias e analise do ativo.
    """
    logger.info("[%s] iniciando", ticker)

    indicadores = coletar_indicadores(ticker, nome_empresa)
    noticias = coletar_noticias(ticker, nome_empresa)
    analise = gerar_analise(ticker, nome_empresa, indicadores, noticias)

    # Injeta sentimento e justificativa nas notícias cruzando pelo título
    classificadas = {n["titulo"]: n for n in analise.get("noticias_classificadas", [])}
    for noticia in noticias:
        match = classificadas.get(noticia["titulo"], {})
        noticia["sentimento"] = match.get("sentimento", "neutro")
        noticia["justificativa"] = match.get("justificativa", "")

    return {
        "ticker": ticker,
        "nome_empresa": nome_empresa,
        "indicadores": indicadores,
        "noticias": noticias,
        "analise": analise,
    }


def main() -> None:
    """Ponto de entrada do orquestrador."""
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY não encontrada — configure o .env")
        sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY não encontrada — configure o .env")
        sys.exit(1)

    ativos = carregar_ativos(ATIVOS_PATH)
    logger.info("Iniciando briefing — %d ativos", len(ativos))

    inicio = time.time()
    resultados = {}
    erros = []

    for ticker, nome_empresa in ativos:
        try:
            resultados[ticker] = processar_ativo(ticker, nome_empresa)
        except Exception as e:
            logger.error("[%s] falha: %s", ticker, e)
            erros.append(ticker)

    hoje = date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
