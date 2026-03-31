-- gold_asai3_balance.sql
-- ASAI3 — Balance Sheet (Assets 1.xx + Liabilities/Equity 2.xx)

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '06057223000171'
  and (account_code like '1.%' or account_code like '2.%')
order by ref_date desc, account_code
