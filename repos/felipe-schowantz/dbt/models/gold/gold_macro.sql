-- gold_macro.sql
-- BCB macro indicators — one row per date (latest extraction wins).
--
-- Series and units:
--   selic_rate        — Selic target rate (% per year), BCB series 432. Daily.
--   ipca_monthly      — Monthly CPI inflation (% MoM), BCB series 433. Monthly (others = NULL).
--   unemployment_rate — PNAD unemployment rate (%), BCB series 24369. Quarterly (others = NULL).
--   usd_brl_rate      — USD/BRL commercial exchange rate, BCB series 1. Business days only (weekends/holidays = NULL).
--   trade_balance     — Monthly trade balance (USD million FOB), BCB series 22707. Monthly (others = NULL).

select distinct on (ref_date)
    ref_date,
    selic_rate,
    ipca_monthly,
    unemployment_rate,
    usd_brl_rate,
    trade_balance
from {{ ref('stg_bcb') }}
where ref_date is not null
order by ref_date desc, _extracted_at desc
