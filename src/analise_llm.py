"""Módulo de análise fundamentalista via LLM (Claude)."""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """Você é um analista de value investing focado em qualidade de negócio e proteção de downside.

Analise o ativo abaixo com base nos indicadores fundamentalistas e nas notícias recentes.

## Ativo
Ticker: {ticker}
Empresa: {nome_empresa}

## Indicadores Fundamentalistas
{indicadores_json}

## Notícias Recentes (últimos 7 dias)
{noticias_resumo}

## Instrução
Responda EXCLUSIVAMENTE com um JSON puro (sem markdown, sem texto adicional) com a seguinte estrutura:
{{
  "resumo_negocio": "parágrafo descrevendo o modelo de negócio e posição competitiva",
  "interpretacao_indicadores": "parágrafo interpretando os indicadores sob a ótica de value investing",
  "noticias_classificadas": [
    {{
      "titulo": "título da notícia",
      "sentimento": "positivo|negativo|neutro",
      "justificativa": "uma frase explicando o impacto"
    }}
  ],
  "perguntas_investigativas": [
    "pergunta 1",
    "pergunta 2",
    "pergunta 3"
  ]
}}"""


def gerar_analise(
    ticker: str,
    nome_empresa: str,
    indicadores: dict,
    noticias: list[dict],
) -> dict:
    """Gera análise fundamentalista completa via Claude.

    Consolida indicadores e notícias em um prompt e solicita ao Claude uma
    análise estruturada sob a ótica de value investing.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").
        indicadores: Dict com indicadores fundamentalistas coletados.
        noticias: Lista de dicts com notícias recentes.

    Returns:
        Dict com chaves: resumo_negocio, interpretacao_indicadores,
        noticias_classificadas e perguntas_investigativas.
        Retorna dict com chave "erro" se o parsing falhar.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    indicadores_json = json.dumps(indicadores, ensure_ascii=False, indent=2) if indicadores else "{}"

    if noticias:
        noticias_resumo = "\n".join(
            f"- {n['titulo']} ({n['fonte']})" for n in noticias
        )
    else:
        noticias_resumo = "Nenhuma notícia encontrada no período."

    prompt = _PROMPT_TEMPLATE.format(
        ticker=ticker,
        nome_empresa=nome_empresa,
        indicadores_json=indicadores_json,
        noticias_resumo=noticias_resumo,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        texto = response.content[0].text.strip()

        # Remove possíveis marcações de código
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
            texto = texto.strip()

        analise = json.loads(texto)
        logger.info("[%s] análise gerada", ticker)
        return analise

    except json.JSONDecodeError as e:
        logger.warning("[%s] falha ao parsear análise: %s", ticker, e)
        return {"erro": f"Falha no parsing da resposta: {e}"}
    except Exception as e:
        logger.warning("[%s] erro na análise: %s", ticker, e)
        return {"erro": str(e)}
