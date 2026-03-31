import json
from urllib import error, request

import pandas as pd


def summarize_price_data(dataframe):
    if dataframe is None or dataframe.empty or "Close" not in dataframe.columns:
        return {}

    close_series = pd.to_numeric(dataframe["Close"], errors="coerce").dropna()
    if close_series.empty:
        return {}

    first_price = float(close_series.iloc[0])
    last_price = float(close_series.iloc[-1])
    pct_change = ((last_price / first_price) - 1) * 100 if first_price else None

    return {
        "primeiro_fechamento": first_price,
        "ultimo_fechamento": last_price,
        "minimo_periodo": float(close_series.min()),
        "maximo_periodo": float(close_series.max()),
        "variacao_percentual": pct_change,
    }


def generate_structured_report_with_llm(
    ticker,
    info_dict,
    period_label,
    price_summary,
    parsed_news,
    api_key,
    timeout=60,
):
    if not api_key:
        return None, (
            "Chave de API não encontrada. Configure GOOGLE_API_KEY em variável de ambiente "
            "ou no secrets do Streamlit para gerar o relatório."
        )

    report_payload = {
        "ticker": ticker,
        "periodo_analise": period_label,
        "empresa": {
            "nome": info_dict.get("Nome"),
            "setor": info_dict.get("Setor"),
            "industria": info_dict.get("Indústria"),
            "descricao": info_dict.get("Descrição"),
        },
        "fundamentos": {
            "P/L": info_dict.get("P/L"),
            "ROE": info_dict.get("ROE"),
            "Dívida/Equity": info_dict.get("Dívida/Equity"),
            "Margem Líquida": info_dict.get("Margem Líquida"),
            "DY": info_dict.get("DY"),
            "Preço Atual": info_dict.get("Preço Atual"),
            "Moeda": info_dict.get("Moeda"),
        },
        "preco": price_summary,
        "noticias": parsed_news[:8],
    }

    system_prompt = (
        "Você é um analista financeiro sênior. Gere um relatório em português do Brasil, "
        "com linguagem objetiva e sem recomendar compra ou venda."
    )
    user_prompt = (
        "Com base nos dados abaixo, gere um relatório estruturado em Markdown com EXATAMENTE estas seções:\n"
        "## Resumo do negócio\n"
        "- Escreva 2-3 frases sobre o negócio e contexto atual.\n\n"
        "## Interpretação dos indicadores fundamentalistas\n"
        "- Interprete os indicadores (não apenas repita números), explicando o que sugerem sobre rentabilidade, eficiência, alavancagem e risco.\n"
        "- Se houver lacunas de dados, explicite limitações.\n\n"
        "## Síntese das notícias por sentimento\n"
        "- Classifique as notícias em Positivas, Negativas ou Neutras.\n"
        "- Para cada classe, traga um resumo curto do racional e cite títulos relevantes.\n"
        "- Se não houver notícias suficientes, indique.\n\n"
        "## Três perguntas para investigação adicional\n"
        "1. ...\n2. ...\n3. ...\n\n"
        "Dados coletados (JSON):\n"
        f"{json.dumps(report_payload, ensure_ascii=False)}"
    )

    combined_prompt = f"{system_prompt}\n\n{user_prompt}"

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": combined_prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

    req = request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            message = response_data["candidates"][0]["content"]["parts"][0]["text"]
            return message, None
    except error.HTTPError as http_err:
        try:
            err_body = http_err.read().decode("utf-8")
        except Exception:
            err_body = str(http_err)
        return None, f"Erro HTTP na chamada ao Gemini: {err_body}"
    except Exception as ex:
        return None, f"Falha ao gerar relatório com Gemini: {ex}"
