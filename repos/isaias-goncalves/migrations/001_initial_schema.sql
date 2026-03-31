-- Migração Inicial: Criação do Esquema Base

-- Tabela de Versão do Banco
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Empresas (Dados Estáticos)
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    business_summary TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Indicadores de Mercado (Dados Dinâmicos)
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price REAL,
    p_l REAL,
    roe REAL,
    dy REAL,
    net_margin REAL,
    debt_ebitda REAL,
    FOREIGN KEY (ticker) REFERENCES companies (ticker)
);

-- Tabela de Notícias (Deduplicada via news_hash)
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    published_at TIMESTAMP,
    title TEXT NOT NULL,
    link TEXT,
    publisher TEXT,
    news_hash TEXT UNIQUE,
    FOREIGN KEY (ticker) REFERENCES companies (ticker)
);

-- Tabela de Análises de IA
CREATE TABLE IF NOT EXISTS ai_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT,
    business_summary_ai TEXT,
    indicator_analysis TEXT,
    sentiment_class TEXT,
    sentiment_analysis TEXT,
    investigative_questions TEXT, -- Armazenado como JSON string
    FOREIGN KEY (ticker) REFERENCES companies (ticker)
);

-- Registrar a versão 1
INSERT INTO schema_version (version) VALUES (1);
