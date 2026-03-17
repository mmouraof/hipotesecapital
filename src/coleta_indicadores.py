"""Módulo de coleta de indicadores fundamentalistas via OpenAI com web search."""

import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


def coletar_indicadores(ticker: str, nome_empresa: str) -> dict:
    """Coleta indicadores fundamentalistas de um ativo via GPT-4o com web search.

    Usa a Responses API da OpenAI com a ferramenta web_search_preview para
    extrair P/L, P/VP, ROE, Dividend Yield, Dívida Líquida/EBITDA, Margem
    Líquida e EV/EBITDA do Investidor10.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dicionário com os indicadores extraídos. Valores ausentes ficam como None.
        Retorna dicionário vazio se a coleta falhar.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"

    prompt = (
        f"Acesse a página {url} e extraia os seguintes indicadores fundamentalistas de {nome_empresa} ({ticker}): "
        "P/L, P/VP, ROE, Dividend Yield, Dívida Líquida/EBITDA, Margem Líquida. "
        "Para cada indicador não encontrado nessa página, busque em fontes alternativas como "
        "Status Invest ou Fundamentus antes de retornar null. "
        "Use null apenas se o valor for confirmadamente indisponível em todas as fontes consultadas. "
        "Retorne SOMENTE um JSON puro (sem markdown, sem explicação) com exatamente estas chaves: "
        "\"P/L\", \"P/VP\", \"ROE\", \"Dividend Yield\", \"Dívida Líquida/EBITDA\", \"Margem Líquida\"."
    )

    try:
        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )

        texto = response.output_text.strip()

        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
            texto = texto.strip()

        indicadores = json.loads(texto)
        logger.info("[%s] indicadores coletados", ticker)
        return indicadores

    except json.JSONDecodeError as e:
        logger.warning("[%s] falha ao parsear indicadores: %s", ticker, e)
        return {}
    except Exception as e:
        logger.warning("[%s] erro na coleta de indicadores: %s", ticker, e)
        return {}
