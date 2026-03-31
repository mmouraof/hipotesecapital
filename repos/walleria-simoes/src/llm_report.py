import os
import logging
from google import genai
from typing import Dict

logger = logging.getLogger(__name__)

def generate_report(company_data: Dict) -> str:
    """Send the collected data to Gemini to generate a structured report using the new SDK."""
    
    if company_data.get("Name") in ["INVALID TICKER", "N/A", None]:
        logger.error("The report could not be generated: Company data not found.")
        return "The report could not be generated: Company data not found."

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("Error: GEMINI_API_KEY not configured in the .env file.")
        return "Error: GEMINI_API_KEY not configured in the .env file."
    
    try:
        client = genai.Client(api_key=api_key)
        
        news_text = company_data.get('Recent News') or company_data.get('Recent news', 'N/A')
        
        prompt = f"""

        Regras de Segurança:
        1. Baseie-se ESTRITAMENTE e EXCLUSIVAMENTE nos dados fornecidos neste prompt.
        2. Se não houver dados suficientes para chegar a uma conclusão, escreva: 'Dados insuficientes para análise'.
        3. JAMAIS invente números, múltiplos ou cite notícias que não estejam listadas abaixo.

        Você é um analista fundamentalista sênior de um fundo de investimentos em ações que segue a filosofia de Value Investing. Você também utiliza análise fundamentalista com abordagem bottom-up para identificar ativos cujos preços de mercado estejam consideravelmente inferiores aos seus valores intrínsecos.
        Sua tarefa é ler os dados brutos da empresa {company_data.get('Name')} ({company_data.get('Ticker')}) e gerar um relatório estruturado, direto ao ponto e analisando sob a ótica de value investing, priorizando qualidade do negócio e proteção de downside. 

        --- DADOS EXTRAÍDOS ---
        Setor: {company_data.get('Sector')}
        Segmento: {company_data.get('Segment')}
        Preço Atual: R$ {company_data.get('Current Price')}
        
        [MÚLTIPLOS FINANCEIROS]
        P/L: {company_data.get('P/L')}
        ROE (%): {company_data.get('ROE (%)')}
        Dívida Líq/EBITDA: {company_data.get('Net Debt/EBITDA')}
        Margem Líquida (%): {company_data.get('Net Profit Margin (%)')}
        Dividend Yield (%): {company_data.get('Dividend Yield (%)')}
        
        [MODELO DE NEGÓCIO]
        {company_data.get('Business Model')}
        
        [NOTÍCIAS RECENTES]
        {news_text}
        -----------------------

        O seu relatório DEVE conter EXATAMENTE os seguintes 4 tópicos, utilizando formatação Markdown (negrito, listas, etc.):

        ### 1. Resumo do Negócio
        Escreva de 2 a 3 frases sintetizando o que a empresa faz, como ela ganha dinheiro e seu posicionamento no setor.

        ### 2. Interpretação dos Indicadores Fundamentalistas
        Não apenas liste os números. Explique o que eles sugerem. A empresa está cara ou barata? É rentável? A dívida está controlada? O dividendo é atrativo para a categoria dela? Considere as particularidades do setor (ex: bancos não possuem EBITDA).

        ### 3. Síntese do Noticiário
        Classifique o sentimento geral das notícias fornecidas como [Positivo], [Negativo] ou [Neutro]. Escreva um parágrafo justificando essa classificação com base nas manchetes.

        ### 4. Checklist do Analista
        Liste 3 perguntas cruciais (em formato de bullet points) que um analista de *equity research* DEVE investigar mais a fundo antes de recomendar a compra ou venda desta ação.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'temperature': 0.0}
        )
        
        return response.text
        
    except Exception as e:
        logger.error(f"Error generating report with Gemini: {e}")
        return f"Error generating report with Gemini: {e}"