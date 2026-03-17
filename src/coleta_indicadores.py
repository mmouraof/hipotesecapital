"""Módulo de coleta de indicadores fundamentalistas via API do Claude com web_fetch."""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)


def coletar_indicadores(ticker: str, nome_empresa: str) -> dict:
    """Coleta indicadores fundamentalistas de um ativo via Claude web_fetch.

    Acessa o Investidor10 usando a ferramenta web_fetch do Claude para extrair
    P/L, P/VP, ROE, Dividend Yield, Dívida Líquida/EBITDA, Margem Líquida e EV/EBITDA.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dicionário com os indicadores extraídos. Valores ausentes ficam como None.
        Retorna dicionário vazio se a coleta falhar.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"

    prompt = (
        f"Acesse a página {url} e extraia APENAS os seguintes indicadores em formato "
        "JSON puro (sem markdown, sem explicação): P/L, P/VP, ROE, Dividend Yield, "
        "Dívida Líquida/EBITDA, Margem Líquida, EV/EBITDA. "
        "Se algum não estiver disponível, use null."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": 3,
                }
            ],
            extra_headers={"anthropic-beta": "web-fetch-2025-09-10"},
        )

        # Extrai o texto da resposta (último bloco de texto)
        texto = ""
        for block in response.content:
            if block.type == "text":
                texto = block.text

        # Remove possíveis marcações de código antes de parsear
        texto = texto.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
            texto = texto.strip()

        indicadores = json.loads(texto)
        logger.info("Indicadores coletados para %s: %s", ticker, list(indicadores.keys()))
        return indicadores

    except json.JSONDecodeError as e:
        logger.warning("Falha ao parsear JSON dos indicadores de %s: %s", ticker, e)
        return {}
    except Exception as e:
        logger.warning("Erro ao coletar indicadores de %s: %s", ticker, e)
        return {}
