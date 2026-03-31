import yfinance as yf
import pandas as pd
from curl_cffi import requests as requests_cffi
from typing import Dict, Optional, Any, List, Union
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from config import NEWS_LIMIT, DEFAULT_HISTORY_PERIOD, NEWS_MAX_AGE_DAYS
from utils.logger import logger

class DataCollector:
    """
    Orquestra a coleta de dados de mercado, fundamentalistas e notícias.
    
    Atua como um wrapper sobre o yfinance e Google News RSS, garantindo 
    resiliência via mimetismo de navegador (curl_cffi) e filtragem temporal.
    
    Attributes:
        ticker_symbol (str): Ticker formatado (ex: PETR4.SA).
        session (requests_cffi.Session): Sessão com impersonate="chrome".
        ticker (yf.Ticker): Objeto yfinance inicializado.
    """
    
    def __init__(self, ticker: str) -> None:
        """
        Inicializa o coletor para um ticker específico.
        
        Args:
            ticker: Código da empresa (com ou sem .SA).
        """
        self.ticker_symbol = ticker.upper() if ticker.upper().endswith(".SA") else f"{ticker.upper()}.SA"
        self.session = requests_cffi.Session(impersonate="chrome", verify=False)
        self.ticker = yf.Ticker(self.ticker_symbol, session=self.session)

    def _is_recent(self, date_str: Union[str, int, None]) -> bool:
        """
        Valida se uma data de publicação está dentro da janela configurada.
        
        Args:
            date_str: Data em formato string (ISO/RFC) ou timestamp unix.
            
        Returns:
            bool: True se a notícia for recente ou se a data for inválida.
        """
        if not date_str:
            return True
            
        try:
            # Tratamento para timestamp vindo do Yahoo
            if isinstance(date_str, int):
                publish_date = datetime.fromtimestamp(date_str, tz=timezone.utc)
            else:
                publish_date = date_parser.parse(str(date_str))
            
            if publish_date.tzinfo is None:
                publish_date = publish_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            limit = now - timedelta(days=NEWS_MAX_AGE_DAYS)
            
            return publish_date >= limit
        except Exception as e:
            logger.warning(f"CL: Falha ao validar data da notícia'{date_str}': {e}")
            return True

    def collect_all_data(self) -> Dict[str, Any]:
        """
        Executa o pipeline completo de extração de dados brutos.
        
        Returns:
            Dict[str, Any]: Dicionário contendo cadastral, market_indicators e news.
        """
        logger.info(f"CL: Iniciando extração: {self.ticker_symbol}")
        
        try:
            # Otimização: Pegamos o info uma única vez
            info = self.ticker.info
            
            if not info or 'symbol' not in info:
                logger.error(f"CL: (API) Ticker {self.ticker_symbol} inválido ou deslistado.")
                return {}

            return {
                "cadastral": self._get_cadastral_data(info),
                "market_indicators": self._get_market_indicators(info),
                "news": self._get_recent_news(limit=NEWS_LIMIT)
            }
            
        except Exception as e:
            logger.error(f"CL: Falha catastrófica na coleta ({self.ticker_symbol}): {str(e)}")
            return {}

    def _get_cadastral_data(self, info: Dict[str, Any]) -> Dict[str, str]:
        """Extrai perfil corporativo e modelo de negócio."""
        return {
            "nome": info.get("longName", "N/A"),
            "setor": info.get("sector", "N/A"),
            "segmento": info.get("industry", "N/A"),
            "resumo": info.get("longBusinessSummary", "N/A")
        }

    def _get_market_indicators(self, info: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Mapeia indicadores chave para a tese de Value Investing."""
        return {
            "preco_atual": info.get("currentPrice"),
            "p_l": info.get("trailingPE"),
            "roe": info.get("returnOnEquity"),
            "divida_ebitda": info.get("debtToEbitda"),
            "margem_liquida": info.get("profitMargins"),
            "dy": info.get("dividendYield")
        }

    def _get_recent_news(self, limit: int = NEWS_LIMIT) -> List[Dict[str, str]]:
        """
        Coleta notícias de múltiplas fontes com filtragem temporal.
        
        Args:
            limit: Quantidade máxima de notícias.
            
        Returns:
            List[Dict[str, str]]: Lista de dicionários com title, link e publisher.
        """
        news: List[Dict[str, str]] = []
        
        # 1. Yahoo Finance
        try:
            yf_news = self.ticker.news
            if yf_news:
                for n in yf_news:
                    content = n.get("content", n)
                    pub_date = content.get("pubDate") or n.get("providerPublishTime")
                    
                    if not self._is_recent(pub_date):
                        continue

                    title = content.get("title") or content.get("headline")
                    if title:
                        news.append({
                            "title": str(title),
                            "link": content.get("canonicalUrl", {}).get("url") or n.get("link", "#"),
                            "publisher": content.get("provider", {}).get("displayName") or n.get("publisher", "Yahoo Finance")
                        })
                    if len(news) >= limit: break
        except Exception as e:
            logger.warning(f"CL: (API) Yahoo News indisponível: {e}")

        # 2. Fallback Google News (RSS)
        if len(news) < limit:
            try:
                clean_ticker = self.ticker_symbol.split(".")[0]
                url = f"https://news.google.com/rss/search?q={clean_ticker}+B3&hl=pt-BR&gl=BR&ceid=BR:pt-419"
                resp = self.session.get(url, timeout=10)
                
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.content, features="xml")
                    for item in soup.find_all("item"):
                        if not self._is_recent(item.pubDate.text if item.pubDate else None):
                            continue
                            
                        title = item.title.text if item.title else None
                        if title and not any(title[:30] in n["title"] for n in news):
                            news.append({
                                "title": str(title),
                                "link": item.link.text if item.link else "#",
                                "publisher": item.source.text if item.source else "Google News"
                            })
                        if len(news) >= limit: break
            except Exception as e:
                logger.error(f"CL: (API) Google News Fallback falhou: {e}")

        return news[:limit]

    def get_history(self, period: str = DEFAULT_HISTORY_PERIOD) -> pd.DataFrame:
        """Retorna série temporal de preços do ativo."""
        return self.ticker.history(period=period)
