-- Cria o banco do projeto (separado do banco do Airflow)
CREATE DATABASE hipotetical_fia;

-- Conecta ao banco hipotetical_fia e cria os schemas
\connect hipotetical_fia;

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- ── Tabelas de staging (preenchidas pelo postgres_loader.py) ─────────────────

CREATE TABLE IF NOT EXISTS staging.raw_bcb (
    data               TEXT,
    selic_meta         TEXT,
    ipca_mensal        TEXT,
    desemprego         TEXT,
    cambio_usd_brl     TEXT,
    balanco_comercial  TEXT,
    _extracted_at      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS staging.raw_yfinance (
    ticker              TEXT,
    "shortName"         TEXT,
    sector              TEXT,
    "marketCap"         TEXT,
    "currentPrice"      TEXT,
    "trailingPE"        TEXT,
    "priceToBook"       TEXT,
    "enterpriseToEbitda" TEXT,
    "returnOnEquity"    TEXT,
    "profitMargins"     TEXT,
    "ebitdaMargins"     TEXT,
    "dividendYield"     TEXT,
    "debtToEquity"      TEXT,
    "totalRevenue"      TEXT,
    "netIncomeToCommon" TEXT,
    _extracted_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS staging.raw_cvm (
    "CNPJ_CIA"       TEXT,
    "DENOM_CIA"      TEXT,
    "CD_CVM"         TEXT,
    "DT_REFER"       TEXT,
    "VERSAO"         TEXT,
    "GRUPO_DFP"      TEXT,
    "MOEDA"          TEXT,
    "ESCALA_MOEDA"   TEXT,
    "ORDEM_EXERC"    TEXT,
    "DT_INI_EXERC"   TEXT,
    "DT_FIM_EXERC"   TEXT,
    "CD_CONTA"       TEXT,
    "DS_CONTA"       TEXT,
    "VL_CONTA"       TEXT,
    "ST_CONTA_FIXA"  TEXT,
    _statement       TEXT,
    _source          TEXT,
    _extracted_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS staging.transcripts (
    id              SERIAL PRIMARY KEY,
    ticker          TEXT,
    period          TEXT,
    reference_date  DATE,
    page_number     INTEGER,
    content         TEXT,
    _extracted_at   TIMESTAMPTZ
);
