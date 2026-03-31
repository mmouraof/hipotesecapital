"""
LLM Report — Chat interface
Envia contexto + histórico de mensagens para o LLM e retorna resposta.
Suporta Anthropic (padrão) e OpenAI.
"""

import os

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
API_KEY  = os.getenv("LLM_API_KEY", "")

SYSTEM_PROMPT = """You are an investment analyst assistant for a value investing fund.
You have access to macro indicators, market multiples, financial statements and earnings call transcripts.

Your role:
- Answer questions about the companies based strictly on the data provided
- Flag significant changes in key metrics (revenue, margins, leverage, cash flow)
- Relate findings to a value investing thesis: downside protection, cash generation, leverage trends
- Be concise and factual — no generic qualitative opinions
- Always cite the specific data point you are referencing

If the data does not contain enough information to answer, say so clearly.
Respond in the same language the user writes in."""


def chat(messages: list[dict], context: str) -> str:
    """
    messages: [{"role": "user"|"assistant", "content": str}]
    context:  string returned by rag.build_context()
    """
    system = SYSTEM_PROMPT + f"\n\n# Available Data\n\n{context}"

    if PROVIDER == "anthropic":
        return _anthropic(messages, system)
    else:
        return _openai(messages, system)


def _anthropic(messages: list[dict], system: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _openai(messages: list[dict], system: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=API_KEY)
    full_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content
