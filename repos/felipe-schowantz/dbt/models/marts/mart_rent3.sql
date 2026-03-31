-- mart_rent3.sql
-- Visão consolidada da RENT3 (Localiza Hertz) — Serviços / Mobilidade
-- Join entre múltiplos de mercado (yfinance) e DRE (CVM)

with mercado as (
    select * from {{ ref('stg_yfinance') }}
    where ticker = 'RENT3'
),

dre as (
    select
        data_referencia,
        max(case when codigo_conta = '3.01' then valor end) as receita_liquida,
        max(case when codigo_conta = '3.05' then valor end) as ebit,
        max(case when codigo_conta = '3.11' then valor end) as lucro_liquido
    from {{ ref('stg_cvm') }}
    where cnpj = '16670085000155'
    group by data_referencia
),

macro as (
    select * from {{ ref('stg_bcb') }}
    where data_referencia = (select max(data_referencia) from {{ ref('stg_bcb') }})
),

final as (
    select
        -- identificação
        m.ticker,
        m.nome_empresa,
        m.setor,

        -- preço e mercado
        m.preco_atual,
        m.market_cap,

        -- múltiplos (foco da tese)
        m.pl,
        m.pvp,
        m.ev_ebitda,
        m.roe,
        m.margem_liquida,
        m.margem_ebitda,
        m.dividend_yield,
        m.divida_pl,

        -- DRE (último período disponível)
        d.receita_liquida,
        d.ebit,
        d.lucro_liquido,

        -- contexto macro (serviços sensíveis à SELIC e desemprego)
        macro.selic_meta_pct,
        macro.ipca_mensal_pct,
        macro.desemprego_pct,

        m._extracted_at
    from mercado m
    left join dre d
        on d.data_referencia = (select max(data_referencia) from dre)
    cross join macro
)

select * from final
