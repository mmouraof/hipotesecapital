-- gold_prio3_balance.sql
-- PRIO3 — Balance Sheet

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '10629105000168'
  and (account_code like '1.%' or account_code like '2.%')
order by ref_date desc, account_code
