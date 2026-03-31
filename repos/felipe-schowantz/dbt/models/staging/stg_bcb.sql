-- stg_bcb.sql
-- Silver layer — Banco Central do Brasil
-- Tipagem e limpeza de formatação. Mesmas colunas da raw.

with source as (
    select * from {{ source('staging', 'raw_bcb') }}
),

typed as (
    select
        -- DATE
        cast(data as date)                                              as data,

        -- FLOAT: remove pontos de milhar, troca vírgula por ponto
        cast(replace(replace(selic_meta,       '.', ''), ',', '.') as float)  as selic_meta,
        cast(replace(replace(ipca_mensal,      '.', ''), ',', '.') as float)  as ipca_mensal,
        cast(replace(replace(desemprego,       '.', ''), ',', '.') as float)  as desemprego,
        cast(replace(replace(cambio_usd_brl,   '.', ''), ',', '.') as float)  as cambio_usd_brl,
        cast(replace(replace(balanco_comercial,'.', ''), ',', '.') as float)  as balanco_comercial,

        -- TIMESTAMPTZ
        cast(_extracted_at as timestamptz)                              as _extracted_at

    from source
    where data is not null
)

select * from typed
