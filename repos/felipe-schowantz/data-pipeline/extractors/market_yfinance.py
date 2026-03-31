"""
Extrator — Yahoo Finance (yfinance)
Fonte: finance.yahoo.com (pública, sem autenticação)
Coleta: preço, múltiplos de mercado e margens
Saída: Parquet em data-lakehouse/raw/yfinance/
"""

import yfinance as yf
import pandas as pd
from datetime import date
from pathlib import Path

BRONZE_PATH = Path(__file__).resolve().parents[2] / "data-lakehouse" / "bronze" / "yfinance"

# Campos de interesse do info do yfinance
INFO_FIELDS = [
    "shortName",
    "sector",
    "marketCap",
    "currentPrice",
    "trailingPE",          # P/L
    "priceToBook",         # P/VP
    "enterpriseToEbitda",  # EV/EBITDA
    "returnOnEquity",      # ROE
    "profitMargins",       # Margem Líquida
    "ebitdaMargins",       # Margem EBITDA
    "dividendYield",       # DY
    "debtToEquity",        # Alavancagem
    "totalRevenue",        # Receita
    "netIncomeToCommon",   # Lucro Líquido
]


def extract_yfinance(tickers: list[str]) -> None:
    """
    Coleta dados de mercado para cada ticker e salva em Parquet.
    Tickers no formato B3: ASAI3.SA, PRIO3.SA, RENT3.SA
    """
    rows = []
    for ticker in tickers:
        try:
            yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
            info = yf.Ticker(yf_ticker).info
            row = {"ticker": ticker, "_extracted_at": pd.Timestamp.utcnow()}  # salva sem .SA
            for field in INFO_FIELDS:
                row[field] = info.get(field)
            rows.append(row)
            print(f"[yfinance] {ticker} — coletado")
        except Exception as e:
            print(f"[yfinance] ERRO em {ticker}: {e}")

    if not rows:
        raise RuntimeError("[yfinance] Nenhum ticker coletado.")

    df = pd.DataFrame(rows)

    out_path = BRONZE_PATH / f"yfinance_{date.today().isoformat()}.parquet"
    BRONZE_PATH.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"[yfinance] Salvo em {out_path}")


if __name__ == "__main__":
    extract_yfinance(tickers=["ASAI3.SA", "PRIO3.SA", "RENT3.SA"])
