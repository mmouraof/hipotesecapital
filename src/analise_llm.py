"""Módulo de análise fundamentalista via LLM (Claude + GPT-4o + Gemini)."""

import json
import logging
import os
import re

import anthropic
import google.generativeai as genai
from openai import OpenAI

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """Você é um analista de value investing focado em qualidade de negócio e proteção de downside.

Analise o ativo abaixo com base nos indicadores fundamentalistas coletados e nas notícias recentes.

## Ativo
Ticker: {ticker}
Empresa: {nome_empresa}

## Indicadores Fundamentalistas Coletados (dados brutos completos)
{indicadores_json}

## Notícias Recentes (últimos 7 dias)
{noticias_resumo}

## Instrução
Responda EXCLUSIVAMENTE com um JSON puro (sem markdown, sem texto adicional) com a seguinte estrutura:
{{
  "resumo_negocio": "parágrafo descrevendo o modelo de negócio e posição competitiva",
  "interpretacao_indicadores": "parágrafo interpretando os indicadores sob a ótica de value investing",
  "indicadores_dashboard": [
    ... (selecione entre 8 e 12 dos indicadores mais relevantes para value investing)
  ],
  "noticias_classificadas": [
    {{
      "titulo": "título EXATO da notícia, copiado da lista acima",
      "relevante": true,
      "sentimento": "positivo ou negativo ou neutro — analise o título com cuidado; use neutro SOMENTE se for impossível determinar impacto",
      "justificativa": "obrigatório — explique em uma frase o impacto específico desta notícia para o ativo {ticker}; nunca deixe vazio"
    }}
  ],
  "perguntas_investigativas": [
    "pergunta 1",
    "pergunta 2",
    "pergunta 3"
  ]
}}

REGRAS para indicadores_dashboard:
- NÃO inclua Cotação nem Data últ cotação — esses valores são exibidos separadamente no cabeçalho do dashboard
- Selecione entre 8 e 12 indicadores que representem valuation, rentabilidade, endividamento e resultado
- Prefira, nesta ordem: P/L, P/VP, Div.Yield, ROE, ROIC, Mrg. Líq., EV/EBITDA, Dív.Líq./EBITDA, Mrg. Ebit, EV/EBIT, Liq. Corr.
- Se um indicador preferido não estiver disponível, substitua pelo mais relevante disponível nos dados brutos
- Use os valores exatamente como aparecem nos dados brutos (não reformate nem calcule)

REGRAS para noticias_classificadas:
- Inclua TODAS as notícias listadas acima, uma por uma, na mesma ordem
- Para cada notícia, defina "relevante": true se a notícia tratar diretamente de {ticker} ou {nome_empresa}; false se for sobre outro ativo, setor geral ou tema sem relação direta com a empresa
- O campo "justificativa" é OBRIGATÓRIO em todos os itens — nunca retorne string vazia ou null
- Prefira "positivo" ou "negativo" sempre que o título indicar qualquer tendência; reserve "neutro" para notícias genuinamente sem impacto identificável"""


_PROMPT_SINTESE = """Você é um editor sênior de análises financeiras de value investing. Receberá duas análises independentes do mesmo ativo, produzidas por modelos de linguagem diferentes.

Sua tarefa é EXCLUSIVAMENTE sintetizar e selecionar o melhor conteúdo já produzido. Você NÃO deve gerar novos dados, inferências, números ou informações que não estejam presentes nas análises abaixo.

## Ativo
Ticker: {ticker}
Empresa: {nome_empresa}

## Análise A (Claude)
{analise_claude_json}

## Análise B (GPT-4o)
{analise_gpt_json}

## Instrução
Responda EXCLUSIVAMENTE com um JSON puro (sem markdown, sem texto adicional) com a seguinte estrutura:
{{
  "resumo_negocio": "síntese em EXATAMENTE 3 frases, combinando os pontos mais relevantes das análises A e B — sem adicionar dados novos",
  "interpretacao_indicadores": "escolha o parágrafo mais completo e preciso entre A e B, ou combine trechos complementares — sem adicionar dados novos",
  "indicadores_dashboard": {indicadores_dashboard_json},
  "noticias_classificadas": [
    {{
      "titulo": "título exato da notícia — copie sem alteração",
      "relevante": true,
      "sentimento": "escolha o sentimento mais bem fundamentado entre A e B",
      "justificativa": "escolha ou combine a justificativa mais clara e específica entre A e B — sem adicionar dados novos"
    }}
  ],
  "perguntas_investigativas": [
    "selecione as 3 perguntas mais relevantes e distintas entre as 6 disponíveis (3 de A + 3 de B) — copie as perguntas palavra por palavra, sem reformular nem criar novas"
  ]
}}

REGRAS ABSOLUTAS:
- Não invente dados, números, percentuais, nomes ou fatos que não apareçam nas análises A ou B
- O campo indicadores_dashboard já está preenchido acima — não altere nenhum item
- Para noticias_classificadas, inclua TODAS as notícias na mesma ordem das análises originais; para "relevante", marque true se ao menos uma das análises marcar true
- Para perguntas_investigativas, copie as perguntas exatamente como estão — não reformule"""


def _extrair_json(texto: str) -> dict:
    """Extrai e parseia o bloco JSON mais externo de uma string."""
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        raise json.JSONDecodeError("nenhum bloco JSON encontrado", texto, 0)
    return json.loads(match.group(0))


# Chaves alternativas que o LLM pode usar no lugar de "label" e "valor"
_LABEL_ALIASES = {"label", "nome", "name", "indicador", "key", "chave", "titulo"}
_VALOR_ALIASES = {"valor", "value", "val", "resultado", "dados"}


def _normalizar_analise(analise: dict) -> dict:
    """Garante que indicadores_dashboard use sempre as chaves 'label' e 'valor'.

    LLMs ocasionalmente retornam chaves alternativas (name/value, nome/valor,
    indicador/valor etc.). Esta função normaliza para o formato esperado pelo
    template HTML sem alterar nenhum outro campo.
    """
    items = analise.get("indicadores_dashboard")
    if not isinstance(items, list):
        return analise

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = next((item[k] for k in _LABEL_ALIASES if k in item), None)
        valor = next((item[k] for k in _VALOR_ALIASES if k in item), None)
        if label is not None:
            normalized.append({"label": label, "valor": valor})

    analise["indicadores_dashboard"] = normalized
    return analise


def _gerar_analise_claude(
    ticker: str,
    nome_empresa: str,
    prompt: str,
) -> dict:
    """Chama Claude Sonnet com o prompt de análise."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.content[0].text.strip()
    if response.stop_reason == "max_tokens":
        logger.warning("[%s] Claude: resposta truncada (stop_reason=max_tokens)", ticker)
    analise = _extrair_json(texto)
    logger.info("[%s] análise Claude gerada", ticker)
    return analise


def _gerar_analise_gpt(
    ticker: str,
    nome_empresa: str,
    prompt: str,
) -> dict:
    """Chama GPT-4o com o mesmo prompt de análise."""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.choices[0].message.content.strip()
    analise = _extrair_json(texto)
    logger.info("[%s] análise GPT-4o gerada", ticker)
    return analise


def _sintetizar_gemini(
    ticker: str,
    nome_empresa: str,
    analise_claude: dict,
    analise_gpt: dict,
) -> dict:
    """Chama Gemini 2.5 Flash para sintetizar as duas análises.

    O Gemini não gera dados novos — apenas seleciona e combina os textos
    já produzidos por Claude e GPT-4o.
    """
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    # indicadores_dashboard vem integralmente da análise do Claude
    indicadores_dashboard_json = json.dumps(
        analise_claude.get("indicadores_dashboard", []),
        ensure_ascii=False,
    )

    prompt = _PROMPT_SINTESE.format(
        ticker=ticker,
        nome_empresa=nome_empresa,
        analise_claude_json=json.dumps(analise_claude, ensure_ascii=False, indent=2),
        analise_gpt_json=json.dumps(analise_gpt, ensure_ascii=False, indent=2),
        indicadores_dashboard_json=indicadores_dashboard_json,
    )

    response = model.generate_content(prompt)
    texto = response.text.strip()
    analise = _extrair_json(texto)
    logger.info("[%s] síntese Gemini gerada", ticker)
    return analise


def gerar_analise(
    ticker: str,
    nome_empresa: str,
    indicadores: dict,
    noticias: list[dict],
) -> dict:
    """Gera análise fundamentalista completa via pipeline de três modelos.

    1. Claude Sonnet e GPT-4o analisam independentemente o ativo.
    2. Gemini 2.5 Flash sintetiza as duas análises, selecionando o melhor
       conteúdo de cada campo e resumindo o negócio em 3 frases, sem gerar
       dados novos além do que os dois modelos já produziram.

    Fallbacks: se GPT-4o falhar, retorna a análise do Claude diretamente.
    Se Gemini falhar, idem. Se Claude falhar, tenta retornar a análise do GPT.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").
        indicadores: Dict com todos os indicadores fundamentalistas coletados.
        noticias: Lista de dicts com notícias recentes.

    Returns:
        Dict com chaves: resumo_negocio, interpretacao_indicadores,
        indicadores_dashboard, noticias_classificadas e perguntas_investigativas.
        Retorna dict com chave "erro" se todos os modelos falharem.
    """
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

    # ── Etapa 1: Claude ────────────────────────────────────────────────────
    analise_claude = None
    try:
        analise_claude = _gerar_analise_claude(ticker, nome_empresa, prompt)
    except Exception as e:
        logger.warning("[%s] Claude falhou: %s", ticker, e)

    # ── Etapa 2: GPT-4o (apenas se ambas as chaves estiverem disponíveis) ──
    # GPT-4o só agrega valor se o Gemini puder sintetizar; sem GOOGLE_API_KEY
    # ou sem OPENAI_API_KEY a chamada seria desperdiçada.
    analise_gpt = None
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.info("[%s] GOOGLE_API_KEY ausente — GPT-4o não será chamado", ticker)
    elif not os.environ.get("OPENAI_API_KEY"):
        logger.info("[%s] OPENAI_API_KEY ausente — GPT-4o não será chamado", ticker)
    else:
        try:
            analise_gpt = _gerar_analise_gpt(ticker, nome_empresa, prompt)
        except Exception as e:
            logger.warning("[%s] GPT-4o falhou: %s", ticker, e)

    if analise_claude is None:
        return {"erro": "Análise Claude falhou e é obrigatória."}

    # Sem análise do GPT, retorna Claude diretamente (sem síntese)
    if analise_gpt is None:
        return _normalizar_analise(analise_claude)

    # ── Etapa 3: Gemini 2.5 Flash — síntese ───────────────────────────────

    try:
        return _normalizar_analise(_sintetizar_gemini(ticker, nome_empresa, analise_claude, analise_gpt))
    except Exception as e:
        logger.warning("[%s] Gemini falhou (%s) — retornando análise Claude", ticker, e)
        return _normalizar_analise(analise_claude)
