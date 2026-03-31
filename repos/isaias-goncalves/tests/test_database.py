import pytest
import os
import sqlite3
import pandas as pd
from core.database import DatabaseManager

@pytest.fixture
def db_manager(tmp_path):
    """Providencia uma instância do DatabaseManager com banco temporário."""
    db_file = tmp_path / "test_finance.db"
    # Precisamos criar a pasta de migrations no tmp_path para o teste ser isolado
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    
    # Copia a migração real para a pasta temporária
    with open("migrations/001_initial_schema.sql", "r") as f:
        schema_sql = f.read()
    with open(mig_dir / "001_initial_schema.sql", "w") as f:
        f.write(schema_sql)
        
    return DatabaseManager(db_path=str(db_file), migrations_dir=str(mig_dir))

def test_database_initialization(db_manager):
    """TC01: Verifica se as tabelas foram criadas corretamente."""
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    
    # Verifica tabelas principais
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "companies" in tables
    assert "market_data" in tables
    assert "news" in tables
    assert "ai_analyses" in tables
    assert "schema_version" in tables
    
    conn.close()

def test_save_ticker_run_idempotency(db_manager):
    """TC03/TC04: Testa inserção e idempotência do perfil da empresa."""
    ticker = "WEGE3.SA"
    data = {
        "cadastral": {
            "nome": "WEG S.A.",
            "setor": "Bens Industriais",
            "segmento": "Máquinas e Equipamentos",
            "resumo": "Fabricante de motores elétricos."
        },
        "market_indicators": {"preco_atual": 35.5, "p_l": 25.0},
        "news": [{"title": "WEG anuncia dividendos", "link": "http://link.com", "publisher": "InfoMoney"}]
    }
    analysis = {
        "resumo_negocio": "Líder global.",
        "analise_indicadores": "ROE alto.",
        "sentimento_noticias": {"classe": "Positivo", "analise": "Bom clima."},
        "perguntas_investigativas": ["Pergunta 1?"]
    }
    
    # Primeira execução
    db_manager.save_ticker_run(ticker, data, analysis, "gpt-4o")
    
    # Verifica se a empresa foi salva
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM companies WHERE ticker = ?", (ticker,))
    assert cursor.fetchone()[0] == "WEG S.A."
    
    # Segunda execução (não deve duplicar empresa)
    db_manager.save_ticker_run(ticker, data, analysis, "gpt-4o")
    cursor.execute("SELECT count(*) FROM companies WHERE ticker = ?", (ticker,))
    assert cursor.fetchone()[0] == 1
    
    # Mas deve ter 2 entradas de dados de mercado
    cursor.execute("SELECT count(*) FROM market_data WHERE ticker = ?", (ticker,))
    assert cursor.fetchone()[0] == 2
    
    conn.close()

def test_news_deduplication(db_manager):
    """TC07: Garante que a mesma notícia não seja duplicada."""
    ticker = "VALE3.SA"
    data = {
        "cadastral": {"nome": "Vale"},
        "market_indicators": {},
        "news": [
            {"title": "Notícia Repetida", "link": "link1", "publisher": "Fonte"},
            {"title": "Notícia Repetida", "link": "link1", "publisher": "Fonte"}
        ]
    }
    analysis = {"sentimento_noticias": {}}
    
    db_manager.save_ticker_run(ticker, data, analysis, "test-model")
    
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM news WHERE ticker = ?", (ticker,))
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_get_ticker_history(db_manager):
    """TC06: Valida a recuperação do histórico como DataFrame."""
    ticker = "PETR4.SA"
    for i in range(5):
        data = {
            "cadastral": {"nome": "Petrobras"},
            "market_indicators": {"preco_atual": 30.0 + i},
            "news": []
        }
        db_manager.save_ticker_run(ticker, data, {"sentimento_noticias": {}}, "test")
        
    df = db_manager.get_ticker_history(ticker)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert df["price"].iloc[0] == 30.0
    assert df["price"].iloc[-1] == 34.0
