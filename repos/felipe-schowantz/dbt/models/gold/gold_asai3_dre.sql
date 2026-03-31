-- gold_asai3_dre.sql
-- ASAI3 — Income Statement (DRE)
-- Source: stg_cvm filtered by CNPJ and accounts 3.xx

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '06057223000171'
  and account_code like '3.%'
order by ref_date desc, account_code
