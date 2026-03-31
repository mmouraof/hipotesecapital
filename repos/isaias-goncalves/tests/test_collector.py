import pytest
from typing import Any, Dict
from core.collector import DataCollector

# Dados de exemplo para reutilização nos testes
MOCK_ITUB_INFO = {
    "symbol": "ITUB4.SA",
    "longName": "Itaú Unibanco Holding S.A.",
    "sector": "Financial Services",
    "industry": "Banks - Regional",
    "longBusinessSummary": "Itaú Unibanco Holding S.A. provides various banking products and services.",
    "currentPrice": 32.50,
    "trailingPE": 8.5,
    "returnOnEquity": 0.18,
    "debtToEbitda": 2.1,
    "profitMargins": 0.15,
    "dividendYield": 0.04
}

MOCK_ITUB_NEWS = [
    {
        "content": {
            "title": "Itaú anuncia dividendos",
            "pubDate": "2026-03-20T10:00:00Z",
            "canonicalUrl": {"url": "http://itau.com/news1"},
            "provider": {"displayName": "InfoMoney"}
        }
    },
    {
        "content": {
            "title": "Análise do setor bancário",
            "pubDate": "2026-03-21T10:00:00Z",
            "canonicalUrl": {"url": "http://itau.com/news2"},
            "provider": {"displayName": "Valor"}
        }
    }
]

@pytest.fixture
def mock_ticker(mocker: Any) -> Any:
    """Fixture que intercepta a criação do yfinance.Ticker e retorna um mock."""
    return mocker.patch("yfinance.Ticker")

@pytest.fixture
def mock_session(mocker: Any) -> Any:
    """Fixture que intercepta o curl_cffi.requests para evitar chamadas de rede reais (Google News)."""
    return mocker.patch("src.core.collector.requests_cffi.Session")

def test_collect_all_data_success(mock_ticker: Any, mock_session: Any) -> None:
    """
    Testa o fluxo de sucesso da coleta de dados.
    """
    # Configuramos o comportamento do mock do Ticker
    instance = mock_ticker.return_value
    instance.info = MOCK_ITUB_INFO
    instance.news = MOCK_ITUB_NEWS

    # Criamos o coletor
    collector = DataCollector("ITUB4")
    data = collector.collect_all_data()
    
    # Asserções
    assert data["cadastral"]["nome"] == "Itaú Unibanco Holding S.A."
    assert data["market_indicators"]["preco_atual"] == 32.50
    assert data["market_indicators"]["p_l"] == 8.5
    # O Yahoo agora deve retornar 2 notícias e o Google não deve ser chamado
    assert len(data["news"]) == 2
    assert data["news"][0]["title"] == "Itaú anuncia dividendos"

def test_collect_all_data_partial_info(mock_ticker: Any, mock_session: Any) -> None:
    """
    Testa a resiliência do coletor quando a API retorna dados parciais.
    """
    instance = mock_ticker.return_value
    instance.info = {
        "symbol": "ITUB4.SA",
        "longName": "Itaú Unibanco Holding S.A.",
        "currentPrice": 32.50
    }
    instance.news = []
    
    # Mock para o Google News retornar vazio também para evitar rede real
    session_instance = mock_session.return_value
    session_instance.get.return_value.status_code = 404 

    collector = DataCollector("ITUB4")
    data = collector.collect_all_data()
    
    # Verifica se os campos ausentes foram tratados como None ou N/A
    assert data["market_indicators"].get("dy") is None
    assert data["cadastral"]["setor"] == "N/A"

def test_collect_all_data_not_found(mock_ticker: Any) -> None:
    """
    Testa o comportamento quando o ticker não existe ou a API não retorna nada.
    """
    instance = mock_ticker.return_value
    instance.info = {} # Simula retorno vazio da API
    
    collector = DataCollector("INVALIDO")
    data = collector.collect_all_data()
    
    assert data == {}
