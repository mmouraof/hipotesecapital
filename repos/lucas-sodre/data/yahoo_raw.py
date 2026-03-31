import yfinance as yf
import pandas as pd
import logging
from data.fundamentus_api import get_fundamentus_info


logger = logging.getLogger(__name__)


def _is_missing(value):
    # Considera vazio quando valor é None/NaN.
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _merge_with_fundamentus(info_dict, fundamentus_dict):
    # Preenche somente os campos faltantes vindos do Yahoo.
    if not fundamentus_dict:
        return info_dict

    for key, value in fundamentus_dict.items():
        if key not in info_dict or _is_missing(info_dict.get(key)):
            info_dict[key] = value

    return info_dict

def get_info_ticker(ticker):
    original_ticker = ticker
    try:
        # Fonte principal: Yahoo Finance.
        ticker = yf.Ticker(ticker + ".SA")

        info_raw = ticker.info
        # Coleta os principais campos usados no dashboard.
        # for key, value in info_raw.items():
        #     if type(value) == str:
        #         info_raw[key] = GoogleTranslator(source="en", target="pt").translate(value)
                
        name = info_raw.get("longName")
        sector = info_raw.get("sector")
        industry = info_raw.get("industry")
        summary = info_raw.get("longBusinessSummary")
        pl = info_raw.get("trailingPE")
        roe = info_raw.get("returnOnEquity")
        debt_ebitda = info_raw.get("debtToEquity")  
        margin_liq = info_raw.get("profitMargins")
        div_yield = info_raw.get("trailingAnnualDividendYield")
        price = info_raw.get("currentPrice")
        currency = info_raw["currency"]
        
        info_dict = {
                    "Nome":name, 
                    "Setor": sector,
                    "Indústria": industry,
                    "Descrição": summary,
                    "DY": div_yield,
                    "Preço Atual": price,
                    "Moeda": currency,
                    "P/L": pl,
                    "ROE": roe,
                    "Dívida/Equity": debt_ebitda,
                    "Margem Líquida": margin_liq
                    }

        # Fallback complementar: Fundamentus para lacunas pontuais.
        fundamentus_info = get_fundamentus_info(original_ticker)
        info_dict = _merge_with_fundamentus(info_dict, fundamentus_info)
        return info_dict
    except:
        # Se Yahoo falhar, tenta pelo menos retornar o Fundamentus.
        fundamentus_info = get_fundamentus_info(original_ticker)
        if fundamentus_info:
            return fundamentus_info
        logger.warning("Nao foi possivel encontrar o ticker: %s", original_ticker)
        return None
        
    
def get_price_history(ticker, period):
    try:
        ticker = yf.Ticker(ticker + ".SA")
        
        # Histórico de preço no período selecionado no dashboard.
        hist = ticker.history(period=period)
        
        # Garante Date como coluna para facilitar o chart.
        hist = hist.reset_index()
        
        return hist[["Date", "Close"]]
    
    except:
        logger.warning("Erro ao buscar historico de precos para ticker: %s", ticker)
        return None
    
def get_news(ticker):
    try:
        # Notícias brutas; normalização acontece em outra camada.
        ticker = yf.Ticker(ticker + ".SA")
        news = ticker.news
        return news
    except:
        logger.warning("Erro ao buscar noticias para ticker: %s", ticker)
        return None