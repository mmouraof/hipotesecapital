-- stg_cvm.sql
-- Silver layer — CVM (ITR/DFP)
-- Tipagem e limpeza de formatação. Mesmas colunas da raw.

with source as (
    select * from {{ source('staging', 'raw_cvm') }}
),

typed as (
    select
        -- VARCHAR
        cast("CNPJ_CIA"      as varchar)   as "CNPJ_CIA",
        cast("DENOM_CIA"     as varchar)   as "DENOM_CIA",
        cast("CD_CVM"        as varchar)   as "CD_CVM",
        cast("GRUPO_DFP"     as varchar)   as "GRUPO_DFP",
        cast("MOEDA"         as varchar)   as "MOEDA",
        cast("ESCALA_MOEDA"  as varchar)   as "ESCALA_MOEDA",
        cast("ORDEM_EXERC"   as varchar)   as "ORDEM_EXERC",
        cast("CD_CONTA"      as varchar)   as "CD_CONTA",
        cast("DS_CONTA"      as varchar)   as "DS_CONTA",
        cast("ST_CONTA_FIXA" as varchar)   as "ST_CONTA_FIXA",
        cast("VERSAO"        as varchar)   as "VERSAO",

        -- DATE
        cast("DT_REFER"      as date)      as "DT_REFER",
        cast("DT_INI_EXERC"  as date)      as "DT_INI_EXERC",
        cast("DT_FIM_EXERC"  as date)      as "DT_FIM_EXERC",

        -- FLOAT: remove pontos de milhar, troca vírgula por ponto
        cast(replace(replace("VL_CONTA", '.', ''), ',', '.') as float)  as "VL_CONTA",

        -- TIMESTAMPTZ
        cast(_extracted_at as timestamptz) as _extracted_at

    from source
)

select * from typed
