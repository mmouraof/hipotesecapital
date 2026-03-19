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
    {{"label": "nome exato do indicador", "valor": "valor exato como aparece nos dados brutos"}},
    {{"label": "...", "valor": "..."}},
    ... (8 a 12 itens no total, cada um com exatamente as chaves "label" e "valor")
  ],
  "noticias_classificadas": [
    {{
      "titulo": "título da notícia copiado da lista acima — remova o nome da fonte se aparecer após travessão ou entre parênteses no final (ex: '... - Valor Econômico' ou '... (InfoMoney)')",
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
  "classificacao": {{
    "label": "atrativo ou neutro ou cautela — escolha com base nos indicadores e análises disponíveis",
    "razao": "uma frase objetiva explicando o principal fator da classificação"
  }},
  "resumo_negocio": "síntese em EXATAMENTE 3 frases, combinando os pontos mais relevantes das análises A e B — sem adicionar dados novos",
  "interpretacao_indicadores": [
    {{"titulo": "Valuation", "texto": "parágrafo sobre múltiplos de valuation (P/L, P/VP, EV/EBITDA etc.) — extraído ou combinado das análises A e B, sem dados novos"}},
    {{"titulo": "Rentabilidade", "texto": "parágrafo sobre rentabilidade e margens (ROE, ROIC, Mrg. Líq., Mrg. Ebit etc.) — extraído ou combinado das análises A e B, sem dados novos"}},
    {{"titulo": "Endividamento", "texto": "parágrafo sobre estrutura de capital e endividamento (Dív.Líq./EBITDA, Dívida Bruta, Patrimônio Líquido etc.) — extraído ou combinado das análises A e B, sem dados novos"}}
  ],
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
- Para perguntas_investigativas, copie as perguntas exatamente como estão — não reformule
- Para classificacao.label use exatamente uma das três opções: "atrativo", "neutro" ou "cautela\""""


_PROMPT_ENRIQUECIMENTO = """Você é um editor financeiro. Receberá uma análise fundamentalista e deve:
1. Classificar o ativo como "atrativo", "neutro" ou "cautela" com base no texto da análise
2. Dividir a interpretação dos indicadores em 3 seções temáticas

Não invente dados novos. Use apenas o conteúdo já presente na análise.

## Ativo: {ticker} — {nome_empresa}

## Resumo do Negócio
{resumo}

## Interpretação Original dos Indicadores
{interpretacao}

## Instrução
Responda EXCLUSIVAMENTE com JSON puro (sem markdown, sem texto adicional):
{{
  "classificacao": {{
    "label": "atrativo ou neutro ou cautela",
    "razao": "uma frase objetiva explicando o principal fator"
  }},
  "interpretacao_indicadores": [
    {{"titulo": "Valuation", "texto": "parágrafo sobre múltiplos de valuation extraído do texto original"}},
    {{"titulo": "Rentabilidade", "texto": "parágrafo sobre rentabilidade e margens extraído do texto original"}},
    {{"titulo": "Endividamento", "texto": "parágrafo sobre estrutura de capital e endividamento extraído do texto original"}}
  ]
}}

REGRAS:
- classificacao.label deve ser exatamente uma de: "atrativo", "neutro", "cautela"
- Distribua o conteúdo existente nas 3 seções sem inventar dados — se um tema não tiver cobertura, use o que houver disponível"""


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

    Trata três formatos que LLMs podem retornar:
    - Lista de dicts com chaves alternativas: [{name: ..., value: ...}, ...]
    - Dict plano: {"P/L": "6,20", "ROE": "28%", ...}
    - Lista de strings: ["P/L: 6,20", ...]  (ignoradas, sem informação estruturada)
    """
    items = analise.get("indicadores_dashboard")

    # Formato dict plano: {"P/L": "6,20", ...} → converter para lista
    if isinstance(items, dict):
        items = [{"label": k, "valor": v} for k, v in items.items()]
        analise["indicadores_dashboard"] = items

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

    # Padroniza justificativas de notícias para iniciar com letra maiúscula
    for noticia in analise.get("noticias_classificadas", []):
        justif = noticia.get("justificativa", "")
        if justif and justif[0].islower():
            noticia["justificativa"] = justif[0].upper() + justif[1:]

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


def _enriquecer_analise_haiku(
    ticker: str,
    nome_empresa: str,
    analise_claude: dict,
) -> dict:
    """Chama claude-haiku-4-5 para adicionar classificacao e reestruturar
    interpretacao_indicadores em 3 seções, sem alterar os outros campos.

    Usado como fallback quando Gemini não está disponível.
    """
    interpretacao = analise_claude.get("interpretacao_indicadores", "")
    resumo = analise_claude.get("resumo_negocio", "")
    # Se já vier no formato array (enriquecido anteriormente), não reprocessar
    if isinstance(interpretacao, list):
        return analise_claude

    prompt = _PROMPT_ENRIQUECIMENTO.format(
        ticker=ticker,
        nome_empresa=nome_empresa,
        resumo=resumo,
        interpretacao=interpretacao,
    )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    enriquecimento = _extrair_json(response.content[0].text.strip())
    analise_claude["classificacao"] = enriquecimento["classificacao"]
    analise_claude["interpretacao_indicadores"] = enriquecimento["interpretacao_indicadores"]
    logger.info("[%s] enriquecimento Haiku gerado", ticker)
    return analise_claude


def _enriquecer_analise_gpt_mini(
    ticker: str,
    nome_empresa: str,
    analise_claude: dict,
) -> dict:
    """Chama gpt-4o-mini para adicionar classificacao e reestruturar
    interpretacao_indicadores em 3 seções, sem alterar os outros campos.

    Usado como segundo fallback de enriquecimento quando Haiku falha e
    OPENAI_API_KEY está disponível.
    """
    interpretacao = analise_claude.get("interpretacao_indicadores", "")
    resumo = analise_claude.get("resumo_negocio", "")
    if isinstance(interpretacao, list):
        return analise_claude

    prompt = _PROMPT_ENRIQUECIMENTO.format(
        ticker=ticker,
        nome_empresa=nome_empresa,
        resumo=resumo,
        interpretacao=interpretacao,
    )

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    enriquecimento = _extrair_json(response.choices[0].message.content.strip())
    analise_claude["classificacao"] = enriquecimento["classificacao"]
    analise_claude["interpretacao_indicadores"] = enriquecimento["interpretacao_indicadores"]
    logger.info("[%s] enriquecimento GPT-mini gerado", ticker)
    return analise_claude


def _tentar_enriquecimento(
    ticker: str,
    nome_empresa: str,
    analise_claude: dict,
) -> dict:
    """Tenta enriquecer a análise do Claude com classificacao e interpretacao em seções.

    Ordem de preferência: Haiku → GPT-mini → sem enriquecimento (retorna como está).
    """
    try:
        return _enriquecer_analise_haiku(ticker, nome_empresa, analise_claude)
    except Exception as e:
        logger.warning("[%s] Haiku enriquecimento falhou (%s)", ticker, e)

    if os.environ.get("OPENAI_API_KEY"):
        try:
            return _enriquecer_analise_gpt_mini(ticker, nome_empresa, analise_claude)
        except Exception as e:
            logger.warning("[%s] GPT-mini enriquecimento falhou (%s)", ticker, e)

    logger.warning("[%s] todos os modelos de enriquecimento falharam — retornando Claude sem enriquecimento", ticker)
    return analise_claude


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
        linhas = []
        for n in noticias:
            linha = f"- {n['titulo']} ({n['fonte']})"
            snippet = n.get("snippet", "")
            if snippet:
                linha += f"\n  Contexto: {snippet}"
            linhas.append(linha)
        noticias_resumo = "\n".join(linhas)
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

    # ── Etapa 2: GPT-4o ────────────────────────────────────────────────────
    # Chamado quando: Claude falhou (GPT torna-se primário) OU ambas as chaves
    # estão disponíveis (para síntese Gemini). Sem OPENAI_API_KEY, nunca chamado.
    analise_gpt = None
    if not os.environ.get("OPENAI_API_KEY"):
        logger.info("[%s] OPENAI_API_KEY ausente — GPT-4o não será chamado", ticker)
    elif analise_claude is None or os.environ.get("GOOGLE_API_KEY"):
        try:
            analise_gpt = _gerar_analise_gpt(ticker, nome_empresa, prompt)
        except Exception as e:
            logger.warning("[%s] GPT-4o falhou: %s", ticker, e)
    else:
        logger.info("[%s] GOOGLE_API_KEY ausente e Claude disponível — GPT-4o não será chamado", ticker)

    if analise_claude is None and analise_gpt is None:
        return {"erro": "Análise falhou — nenhum modelo retornou resultado."}

    # Apenas GPT disponível: enriquece e retorna (Haiku falhará sem ANTHROPIC_API_KEY,
    # GPT-mini assumirá o enriquecimento)
    if analise_claude is None:
        analise_gpt = _tentar_enriquecimento(ticker, nome_empresa, analise_gpt)
        return _normalizar_analise(analise_gpt)

    # Sem análise do GPT, enriquece Claude (Haiku → GPT-mini → sem enriquecimento)
    if analise_gpt is None:
        analise_claude = _tentar_enriquecimento(ticker, nome_empresa, analise_claude)
        return _normalizar_analise(analise_claude)

    # ── Etapa 3: Gemini 2.5 Flash — síntese ───────────────────────────────

    try:
        return _normalizar_analise(_sintetizar_gemini(ticker, nome_empresa, analise_claude, analise_gpt))
    except Exception as e:
        logger.warning("[%s] Gemini falhou (%s) — tentando enriquecimento", ticker, e)
        analise_claude = _tentar_enriquecimento(ticker, nome_empresa, analise_claude)
        return _normalizar_analise(analise_claude)
