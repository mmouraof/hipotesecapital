"""
RAG — Retrieval context builder
Busca dados das tabelas gold e transcrições para montar o contexto do LLM.
"""

import os
import psycopg2
import pandas as pd

PG_CONN = dict(
    host=os.getenv("PG_HOST", "postgres"),
    port=os.getenv("PG_PORT", "5432"),
    dbname=os.getenv("PG_DB", "hipotetical_fia"),
    user=os.getenv("PG_USER", "airflow"),
    password=os.getenv("PG_PASSWORD", "airflow"),
)


def _query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(**PG_CONN)
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def build_context(ticker: str) -> str:
    """
    Monta o contexto completo para o LLM:
    - Dados macro (gold_macro)
    - Múltiplos de mercado (gold_market)
    - DRE dos últimos 4 trimestres (gold_{ticker}_dre)
    - Transcrição mais recente (staging.transcripts)
    """
    sections = []

    # 1. Macro
    macro = _query("""
        SELECT ref_date, selic_rate, ipca_monthly, usd_brl_rate, unemployment_rate
        FROM gold.gold_macro
        WHERE ref_date >= NOW() - INTERVAL '12 months'
        ORDER BY ref_date DESC
        LIMIT 12
    """)
    if not macro.empty:
        sections.append("## Macro Indicators (last 12 months)\n" + macro.to_string(index=False))

    # 2. Market multiples
    market = _query("""
        SELECT ticker, company_name, current_price, market_cap,
               pe_ratio, pb_ratio, ev_ebitda, roe, net_margin, ebitda_margin,
               dividend_yield, debt_to_equity
        FROM gold.gold_market
        WHERE ticker = %s
    """, (ticker,))
    if not market.empty:
        sections.append(f"## Market Multiples — {ticker}\n" + market.to_string(index=False))

    # 3. DRE — últimas 4 datas de referência
    dre_table = f"gold.gold_{ticker.lower()}_dre"
    try:
        dre = _query(f"""
            SELECT ref_date, account_code, account_name, account_value, currency_scale
            FROM {dre_table}
            WHERE account_code IN ('3.01', '3.05', '3.07', '3.11')
            ORDER BY ref_date DESC
            LIMIT 20
        """)
        if not dre.empty:
            sections.append(f"## Income Statement — {ticker} (key lines)\n" + dre.to_string(index=False))
    except Exception:
        pass

    # 4. Transcript
    try:
        transcript = _query("""
            SELECT page_number, content
            FROM staging.transcripts
            WHERE ticker = %s
            ORDER BY _extracted_at DESC, page_number ASC
            LIMIT 30
        """, (ticker,))
        if not transcript.empty:
            text = "\n".join(transcript["content"].tolist())
            sections.append(f"## Earnings Call Transcript — {ticker}\n{text[:8000]}")
    except Exception:
        pass

    return "\n\n---\n\n".join(sections)
