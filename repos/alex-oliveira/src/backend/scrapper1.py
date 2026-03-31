import yfinance as yf
from datetime import datetime

from src.backend.scrapper2 import get_news_data



def get_full_data(ticker: str) -> dict:
    
    """
    Coleta dados cadastrais, de cotação e fundamentalistas de uma ação via yfinance.

    Args:
        ticker: Código do ativo (ex: 'PETR4.SA', 'AAPL')

    Returns:
        Dicionário com todas as informações coletadas.
    """

    ativo = yf.Ticker(ticker)
    info = ativo.info

    dados_cadastrais = {
        "nome_empresa":        info.get("longName"),
        "setor":               info.get("sector"),
        "segmento":            info.get("industry"),
        "resumo_negocio":      info.get("longBusinessSummary"),
    }


    hist = ativo.history(period="1d")
    ultima_data = (
        hist.index[-1].strftime("%Y-%m-%d") if not hist.empty else None
    )
    try:
        balanco = ativo.quarterly_balance_sheet
        ultimo_balanco = (
            balanco.columns[0].strftime("%Y-%m-%d")
            if balanco is not None and not balanco.empty
            else None
        )
    except Exception:
        ultimo_balanco = None
    dados_cotacao = {
        "cotacao":          info.get("currentPrice")    or info.get("regularMarketPrice"),
        "data_ultima_cotacao":     ultima_data,
        "minimo_52_semanas":       info.get("fiftyTwoWeekLow"),
        "maximo_52_semanas":       info.get("fiftyTwoWeekHigh"),
        "volume_medio_2_meses":    info.get("twoMonthAverageVolume") or info.get("averageVolume"),
        "valor_de_mercado":        info.get("marketCap"),
        "data_ultimo_balanco":     ultimo_balanco,
        "numero_de_acoes":         info.get("sharesOutstanding"),
    }


    divida_liquida = info.get("totalDebt", 0) - info.get("totalCash", 0)
    ebitda         = info.get("ebitda")
    div_liq_ebitda = round(divida_liquida / ebitda, 2) if ebitda else None

    indicadores = {
        "p_l":                     info.get("trailingPE"),
        "roe":                     info.get("returnOnEquity"),       
        "divida_liquida_ebitda":   div_liq_ebitda,
        "margem_liquida":          info.get("profitMargins"),       
        "dividend_yield":          info.get("dividendYield"),       
    }

    noticias = get_news_data(ticker, 5, 2)

    dados = {
        "ticker":                  ticker.upper(),
        "data_coleta":             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dados_cadastrais":        dados_cadastrais,
        "dados_cotacao":           dados_cotacao,
        "indicadores_fundamentalistas": indicadores,
        "noticias": noticias
    }

    return dados

# Exemplo
# if __name__ == "__main__":
#     print(get_full_data("recv3"))