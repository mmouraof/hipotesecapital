import json
from typing import Dict, Any, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, DEFAULT_MODEL, VALUE_INVESTING_ANALYSIS_PROMPT, SYSTEM_PERSONA
from utils.logger import logger

class InvestmentAnalyzer:
    """
    Analista de Investimentos via LLM.
    
    Consome dados fundamentalistas e notícias para gerar uma síntese 
    qualitativa baseada na filosofia de Value Investing.
    
    Attributes:
        client (OpenAI): Cliente da API OpenAI inicializado.
        model (str): Identificador do modelo GPT em uso.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        """
        Inicializa o analyzer com credenciais e modelo.
        
        Args:
            api_key: Chave OpenAI (fallback para config.py).
            model: Nome do modelo (fallback para config.py).
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or DEFAULT_MODEL
        
        if not self.api_key:
            logger.error("AN: (API) Chave da OpenAI ausente nas configurações.")
            raise ValueError("OpenAI API Key é obrigatória.")
            
        self.client = OpenAI(api_key=self.api_key)

    def analyze_ticker(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orquestra a chamada ao LLM para análise qualitativa de um ticker.
        
        Args:
            ticker: Símbolo do ativo.
            data: Dicionário de dados coletados pelo DataCollector.
            
        Returns:
            Dict[str, Any]: JSON estruturado com a análise ou erro.
        """
        logger.info(f"AN: Iniciando síntese qualitativa (LLM): {ticker}")
        
        prompt = self._build_prompt(ticker, data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PERSONA},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Resposta da OpenAI veio vazia.")
                
            analysis = json.loads(content)
            logger.info(f"AN: Análise LLM concluída para {ticker}")
            return analysis
            
        except Exception as e:
            logger.error(f"AN: (API) Erro na integração com OpenAI ({ticker}): {str(e)}")
            return {"error": f"Não foi possível processar a análise: {str(e)}"}

    def _build_prompt(self, ticker: str, data: Dict[str, Any]) -> str:
        """
        Injeta os dados coletados no template de prompt do analista.
        """
        cadastral = data.get("cadastral", {})
        indicators = data.get("market_indicators", {})
        news = data.get("news", [])
        
        news_titles = "\n- ".join([n.get('title', 'Sem título') for n in news])

        return VALUE_INVESTING_ANALYSIS_PROMPT.format(
            ticker=ticker,
            nome_empresa=cadastral.get('nome', 'N/A'),
            setor=cadastral.get('setor', 'N/A'),
            segmento=cadastral.get('segmento', 'N/A'),
            resumo_negocio=cadastral.get('resumo', 'N/A'),
            p_l=indicators.get('p_l', 'N/A'),
            roe=indicators.get('roe', 'N/A'),
            divida_ebitda=indicators.get('divida_ebitda', 'N/A'),
            margem_liquida=indicators.get('margem_liquida', 'N/A'),
            dy=indicators.get('dy', 'N/A'),
            noticias=news_titles if news_titles else "Nenhuma notícia relevante nos últimos 90 dias."
        )
