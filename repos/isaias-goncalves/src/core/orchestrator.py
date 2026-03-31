from typing import Dict, Any, List, Optional, Tuple
from core.collector import DataCollector
from core.analyzer import InvestmentAnalyzer
from core.database import DatabaseManager
from utils.logger import logger

class AnalyticalOrchestrator:
    """
    O 'Cérebro' do sistema. Coordena a coleta, análise e persistência,
    decidindo entre buscar dados do banco ou da API.
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def get_history_options(self, ticker: str) -> List[str]:
        """Retorna lista de datas de análises disponíveis no banco."""
        return self.db.get_available_analysis_dates(ticker)

    def get_data(self, ticker: str, version: str = "LIVE", model: str = "gpt-4o-mini") -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """
        Ponto único de entrada para obtenção de dados.
        Retorna (data, analysis, is_historical).
        """
        if version == "LIVE":
            logger.info(f"OR: Iniciando pipeline LIVE para {ticker}")
            data, analysis = self._run_live_pipeline(ticker, model)
            return data, analysis, False
        else:
            logger.info(f"OR: Carregando versão histórica ({version}) para {ticker}")
            result = self.db.get_full_run_by_timestamp(ticker, version)
            if result:
                return result["data"], result["analysis"], True
            else:
                logger.error(f"OR: Falha ao carregar versão {version}. Tentando Live.")
                data, analysis = self._run_live_pipeline(ticker, model)
                return data, analysis, False

    def _run_live_pipeline(self, ticker: str, model: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Executa a coleta e análise completa e salva no banco."""
        collector = DataCollector(ticker)
        data = collector.collect_all_data()
        
        if not data:
            raise ValueError(f"Não foi possível coletar dados para {ticker}")

        analyzer = InvestmentAnalyzer(model=model)
        analysis = analyzer.analyze_ticker(ticker, data)
        
        if "error" in analysis:
            raise ValueError(f"Erro na análise de IA: {analysis['error']}")

        # Persistência automática
        self.db.save_ticker_run(ticker, data, analysis, model)
        
        return data, analysis

    def get_historical_trends(self, ticker: str) -> Any:
        """Retorna o DataFrame de histórico para gráficos."""
        return self.db.get_ticker_history(ticker)
