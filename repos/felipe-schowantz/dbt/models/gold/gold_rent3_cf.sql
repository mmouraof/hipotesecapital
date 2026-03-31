-- gold_rent3_cf.sql
-- RENT3 — Cash Flow Statement

select
    ref_date,
    period_end,
    account_code,
    account_name,
    account_value,
    currency_scale
from {{ ref('stg_cvm') }}
where cnpj = '16670085000155'
  and account_code like '6.%'
order by ref_date desc, account_code
