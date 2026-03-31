{{
    config(
        materialized = "incremental",
        incremental_strategy = "append",
        alias = "stg_yfinance"
    )
}}

-- stg_yfinance.sql
-- Normalizes raw Yahoo Finance data: casts types and renames columns to English.
-- NaN strings (from pandas) are converted to NULL before numeric casting.
-- .SA suffix is stripped from ticker (e.g. ASAI3.SA -> ASAI3).
-- Incremental: only processes rows extracted after the latest loaded timestamp.

select
    REPLACE(ticker, '.SA', '')                              as ticker,
    TRIM(REGEXP_REPLACE("shortName", '\s+(ON|PN).*$', ''))  as company_name,
    sector,
    NULLIF("marketCap",          'NaN')::bigint             as market_cap,
    NULLIF("currentPrice",       'NaN')::numeric            as current_price,
    NULLIF("trailingPE",         'NaN')::numeric            as pe_ratio,
    NULLIF("priceToBook",        'NaN')::numeric            as pb_ratio,
    NULLIF("enterpriseToEbitda", 'NaN')::numeric            as ev_ebitda,
    NULLIF("returnOnEquity",     'NaN')::numeric            as roe,
    NULLIF("profitMargins",      'NaN')::numeric            as net_margin,
    NULLIF("ebitdaMargins",      'NaN')::numeric            as ebitda_margin,
    NULLIF("dividendYield",      'NaN')::numeric            as dividend_yield,
    NULLIF("debtToEquity",       'NaN')::numeric            as debt_to_equity,
    NULLIF("totalRevenue",       'NaN')::bigint             as total_revenue,
    NULLIF("netIncomeToCommon",  'NaN')::bigint             as net_income,
    _extracted_at
from {{ source('staging', 'raw_yfinance') }}
where ticker is not null

{% if is_incremental() %}
    and _extracted_at > (
        select coalesce(max(_extracted_at), '1900-01-01'::timestamptz)
        from {{ this }}
    )
{% endif %}
