-- gold_prio3_dre.sql
-- PRIO3 — Income Statement (DRE)

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '10629105000168'
  and account_code like '3.%'
order by ref_date desc, account_code
