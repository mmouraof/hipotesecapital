import pytest
import json
from typing import Any
from core.analyzer import InvestmentAnalyzer


# Simulação de resposta JSON que o LLM enviaria
MOCK_LLM_RESPONSE = {
    "resumo_negocio": "O Itaú Unibanco é o maior banco privado do Brasil, com forte atuação em varejo e atacado.",
    "analise_indicadores": "O P/L de 8.5x sugere um valuation atrativo, e o ROE de 18% demonstra alta eficiência na alocação de capital.",
    "sentimento_noticias": "Positivo: As notícias sobre dividendos reforçam a tese de geração de valor para o acionista.",
    "perguntas_investigativas": [
        "Como a inadimplência no varejo pode afetar o ROE nos próximos trimestres?",
        "Qual a estratégia do banco frente ao avanço das fintechs?",
        "Existe espaço para aumento do payout nos próximos anos?"
    ]
}

@pytest.fixture
def analyzer() -> InvestmentAnalyzer:
    """Fixture que retorna uma instância do InvestmentAnalyzer com chave fictícia."""
    return InvestmentAnalyzer(api_key="sk-fake-key")

def test_analyze_ticker_success(mocker: Any, analyzer: InvestmentAnalyzer) -> None:
    """
    Testa se o analyzer processa corretamente uma resposta de sucesso da OpenAI.
    """
    # Mockando a chamada client.chat.completions.create
    mock_openai = mocker.patch("openai.resources.chat.completions.Completions.create")
    
    # Configuramos o retorno do mock para simular a estrutura da OpenAI
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = json.dumps(MOCK_LLM_RESPONSE)
    mock_openai.return_value = mock_response
    
    # Dados de entrada (o que viria do collector)
    input_data = {
        "cadastral": {"nome": "Itaú Unibanco", "setor": "Financeiro"},
        "market_indicators": {"p_l": 8.5, "roe": 0.18},
        "news": [{"title": "Dividendos anunciados"}]
    }
    
    result = analyzer.analyze_ticker("ITUB4", input_data)
    
    # Asserções
    assert "resumo_negocio" in result
    assert result["resumo_negocio"].startswith("O Itaú")
    assert len(result["perguntas_investigativas"]) == 3
    assert "error" not in result

def test_analyze_ticker_error(mocker: Any, analyzer: InvestmentAnalyzer) -> None:
    """
    Testa o comportamento do analyzer quando a API da OpenAI falha.
    """
    # Mockando para levantar uma exceção
    mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        side_effect=Exception("API Connection Error")
    )
    
    result = analyzer.analyze_ticker("ITUB4", {})
    
    # Verifica se o erro foi capturado e retornado de forma amigável
    assert "error" in result
    assert "API Connection Error" in result["error"]

def test_build_prompt_contains_data(analyzer: InvestmentAnalyzer) -> None:
    """
    Verifica se a construção do prompt inclui os dados passados.
    """
    data = {
        "cadastral": {"nome": "Empresa Teste", "setor": "Tecnologia"},
        "market_indicators": {"p_l": 15},
        "news": [{"title": "Notícia Importante"}]
    }
    
    prompt = analyzer._build_prompt("TEST3", data)
    
    assert "Empresa Teste" in prompt
    assert "Tecnologia" in prompt
    assert "15" in prompt
    assert "Notícia Importante" in prompt
