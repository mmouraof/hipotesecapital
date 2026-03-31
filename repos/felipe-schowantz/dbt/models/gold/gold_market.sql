-- gold_market.sql
-- Yahoo Finance market multiples — latest snapshot per company.
-- Deduplicates by keeping the most recent extraction per ticker.
--
-- Units:
--   current_price   — Last traded price (BRL)
--   market_cap      — Market capitalization (BRL)
--   pe_ratio        — Price / Earnings (trailing 12 months)
--   pb_ratio        — Price / Book value
--   ev_ebitda       — Enterprise Value / EBITDA
--   roe             — Return on Equity (decimal, e.g. 0.15 = 15%)
--   net_margin      — Net profit margin (decimal)
--   ebitda_margin   — EBITDA margin (decimal)
--   dividend_yield  — Dividend yield (decimal)
--   debt_to_equity  — Total debt / Shareholders equity
--   total_revenue   — Last twelve months revenue (BRL)
--   net_income      — Last twelve months net income (BRL)

select distinct on (ticker)
    ticker,
    company_name,
    sector,
    current_price,
    market_cap,
    pe_ratio,
    pb_ratio,
    ev_ebitda,
    roe,
    net_margin,
    ebitda_margin,
    dividend_yield,
    debt_to_equity,
    total_revenue,
    net_income
from {{ ref('stg_yfinance') }}
where ticker is not null
order by ticker, _extracted_at desc
