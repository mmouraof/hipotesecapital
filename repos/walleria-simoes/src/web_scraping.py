import yfinance as yf
import requests
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from typing import Set, Dict
from src.db_manager import *

logger = logging.getLogger(__name__)

def get_available_tickers() -> Set[str]:
    """Extracts the master list of valid tickers (uses DB cache if available)."""
    
    # Attempts to retrieve from the Database (Daily Cache)
    cached_tickers = get_cached_tickers()
    if cached_tickers:
        return cached_tickers
        
    # If it isnt in the bank today, do a scraping
    url = "https://www.fundamentus.com.br/resultado.php"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    tickers = set()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tabela = soup.find('table', {'id': 'resultado'})
        if tabela:
            linhas = tabela.find('tbody').find_all('tr')
            for linha in linhas:
                celulas = linha.find_all('td')
                if celulas:
                    ticker = celulas[0].text.strip()
                    tickers.add(ticker)
                    
        # Save in the DB for future consultations today
        if tickers:
            save_cached_tickers(tickers)
            
    except Exception as e:
        logger.error(f"Error downloading the Fundamentus ticker list: {e}")
        
    return tickers

def collect_business_model(ticker: str, valid_tickers: Set[str]) -> Dict:
    # The default dictionary already starts with a total failure message
    overview = {
        "Ticker": ticker, 
        "Business Model": "Unable to retrieve the business model from the YFinance API or the local database.",
        "BM_Source": "Failed"
    }
    
    if ticker not in valid_tickers:
        return overview
        
    logger.info(f"Scraping Business Model for {ticker} via YFinance...")
    try:
        # First Attempt: YFinance (Real-time API)
        info = yf.Ticker(f"{ticker}.SA").info
        summary = info.get("longBusinessSummary")
        
        if summary:
            overview["Business Model"] = summary
            overview["BM_Source"] = "YFinance"
            return overview
        else:
            raise ValueError("longBusinessSummary not found in YFinance response")
            
    except Exception as e:
        logger.error(f"Error at YFinance for {ticker}: {e}. Trying database fallback...")
        
    # Second Attempt: Fallback to the Local Database
    db_company = get_company_static_data(ticker)
    
    if db_company and db_company.get("Business Model") not in ["N/A", "Not Found", overview["Business Model"], None]:
        overview["Business Model"] = db_company.get("Business Model")
        overview["BM_Source"] = "Database Fallback"
        logger.info(f"Loaded Business Model for {ticker} from local Database fallback.")
        
    return overview

def collect_data(ticker: str, valid_tickers: Set[str]) -> Dict:
    """Collect market data using Fundamentus."""
    data = {
        "Ticker": ticker, "Name": "N/A", "Sector": "N/A", "Segment": "N/A", 
        "Current Price": "N/D", "P/L": "N/D", "ROE (%)": "N/D", 
        "Net Debt/EBITDA": "N/D", "Net Profit Margin (%)": "N/D", "Dividend Yield (%)": 0.0
    }
    
    if ticker not in valid_tickers:
        data["Name"] = "TICKER INVÁLIDO"
        return data
        
    url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'iso-8859-1' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        fund_dict = {}
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            for i in range(0, len(cells), 2): 
                if i + 1 < len(cells):
                    key = cells[i].text.replace('?', '').strip()
                    if key: fund_dict[key] = cells[i+1].text.strip()

        def to_float(val_str):
            if not val_str or val_str in ["-", "", "N/D"]: return None
            try:
                v = val_str.replace('%', '').replace('.', '').replace(',', '.')
                return float(v)
            except ValueError:
                return None

        data["Name"] = fund_dict.get("Empresa", "N/A")
        data["Sector"] = fund_dict.get("Setor", "N/A")
        data["Segment"] = fund_dict.get("Subsetor", "N/A")
        
        preco = to_float(fund_dict.get("Cotação"))
        data["Current Price"] = round(preco, 2) if preco is not None else "N/D"
        
        data["P/L"] = round(to_float(fund_dict.get("P/L")), 2) if to_float(fund_dict.get("P/L")) is not None else "N/D"
        data["ROE (%)"] = round(to_float(fund_dict.get("ROE")), 2) if to_float(fund_dict.get("ROE")) is not None else "N/D"
        
        dy_val = to_float(fund_dict.get("Div. Yield"))
        data["Dividend Yield (%)"] = round(dy_val, 2) if dy_val is not None else 0.0
        
        if ticker in ['ITUB4', 'BBDC4', 'BBDC3', 'BBAS3', 'SANB11', 'BRSR6', 'BPAC11'] or fund_dict.get("Setor") == "Intermediários Financeiros":
            data["Net Debt/EBITDA"] = "N/A (Banco)"
            data["Net Profit Margin (%)"] = "N/A (Banco)" 
        else:
            data["Net Profit Margin (%)"] = round(to_float(fund_dict.get("Marg. Líquida")), 2) if to_float(fund_dict.get("Marg. Líquida")) is not None else "N/D"
            ev = to_float(fund_dict.get("Valor da firma"))
            ev_ebitda = to_float(fund_dict.get("EV / EBITDA"))
            net_debt = to_float(fund_dict.get("Dív. Líquida"))
            
            if ev is not None and ev_ebitda is not None and net_debt is not None and ev_ebitda != 0:
                ebitda = ev / ev_ebitda
                data["Net Debt/EBITDA"] = round(net_debt / ebitda, 2) if ebitda != 0 else "N/D"

    except Exception as e:
        logger.error(f"Error at Fundamentus to {ticker}: {e}")
        
    return data

def collect_news(ticker: str, valid_tickers: Set[str]) -> Dict:
    """Find the 5 most recent news stories on Google News RSS."""
    data = {"Recent News": "No news found."}
    
    if ticker not in valid_tickers:
        return data
    
    url = f"https://news.google.com/rss/search?q={ticker}+Ações+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        if items:
            formatted_news = []
            for index, item in enumerate(items[:5], 1):
                title_element = item.find("title")
                link_element = item.find("link")
                title = title_element.text if title_element is not None else "No title"
                link = link_element.text if link_element is not None else "No link"
                formatted_news.append(f"{index}. {title} - {link}")
                
            data["Recent News"] = "\n".join(formatted_news)
    except Exception as e:
        logger.error(f"Error at searching news to {ticker}: {e}")
        
    return data