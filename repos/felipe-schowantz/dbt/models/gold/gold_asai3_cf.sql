-- gold_asai3_cf.sql
-- ASAI3 — Cash Flow Statement (6.xx)

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '06057223000171'
  and account_code like '6.%'
order by ref_date desc, account_code
