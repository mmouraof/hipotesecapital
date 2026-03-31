import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()

# --- CONFIGURAÇÕES GERAIS DO PROJETO ---
PROJECT_NAME = "Hipótese Capital | Terminal Analítico"
VERSION = "2.0.1"
DEFAULT_TICKER = "ASAI3"
DEFAULT_HISTORY_PERIOD = "1y"
NEWS_LIMIT = 5
NEWS_MAX_AGE_DAYS = 90  # Filtro de 3 meses para as notícias
DB_PATH = os.getenv("DB_PATH", "database.db")


# --- CONFIGURAÇÕES DE IA (LLM) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AVAILABLE_MODELS = ["gpt-4o-mini", "gpt-4o"]

# --- ASSETS DE BRANDING ---
# Mantemos os caminhos para serem usados no código
LOGO_LIGHT = "branding/logo.png"
LOGO_DARK = "branding/logo_dark.png"
ICON_BRAND = "branding/icon_bg.png"

# --- CORES PARA GRÁFICOS E ALERTAS ---
# Usamos essas constantes apenas onde o Streamlit não aplica o tema automaticamente (ex: cores de linhas de gráficos)
CHART_COLOR_PRIMARY = "#660B05" # Vermelho Hipótese
CHART_COLOR_SECONDARY = "#8C1007" 

# --- TEXTOS E DESCRIÇÕES (TOOLTIPS) ---
INDICATOR_TOOLTIPS = {
    "price": "Preço atual ou de fechamento do ativo na data da captura.",
    "p_l": "Preço/Lucro: Indica quanto o mercado está disposto a pagar por cada real de lucro da empresa.",
    "roe": "Return on Equity: Mede a rentabilidade da empresa em relação ao seu patrimônio líquido.",
    "net_margin": "Margem Líquida: Indica a porcentagem de lucro em relação à receita total.",
    "dy": "Dividend Yield: Rendimento gerado por dividendos em relação ao preço da ação.",
    "debt_ebitda": "Dívida Líquida/EBITDA: Mede a alavancagem e a capacidade de pagamento da dívida da empresa."
}

# --- PROMPTS DO SISTEMA (CONSOLIDADO) ---
SYSTEM_PERSONA = """
Você é um Analista de Investimentos Sênior na Hipótese Capital, uma gestora focada em Value Investing.

Hipótese Capital — uma gestora de investimentos fundada por três sócios com passagens pelo sell-
side e asset management — administra um fundo de ações concentrado com R$ 1,2 bilhão sob
gestão. A tese de investimento é clara: poucas posições, convicção alta, horizonte longo. O time de
análise tem seis pessoas. 

"""

VALUE_INVESTING_ANALYSIS_PROMPT = """
Analise a empresa {ticker} ({nome_empresa}) com base nos seguintes dados:

--- DADOS CADASTRAIS ---
Setor: {setor}
Segmento: {segmento}
Resumo do Negócio: {resumo_negocio}

--- INDICADORES DE MERCADO ---
P/L: {p_l}
ROE: {roe}
Dívida Líquida/EBITDA: {divida_ebitda}
Margem Líquida: {margem_liquida}
Dividend Yield: {dy}

--- NOTÍCIAS RECENTES ---
{noticias}

--- INSTRUÇÕES DO ANALISTA SÊNIOR (HIPÓTESE CAPITAL) ---
Você deve agir como um Analista Sênior da Hipótese Capital. Sua filosofia é o Value Investing: busca por empresas de alta qualidade, fossos econômicos (moats) defensáveis e margem de segurança.

Gere um JSON com as seguintes chaves:
1. "resumo_negocio": Uma síntese concisa do modelo de geração de valor (2-3 frases).
2. "analise_indicadores": Interpretação qualitativa. O que esses números dizem sobre a saúde do negócio e a proteção de downside? Seja crítico.
3. "sentimento_noticias": Um objeto contendo:
    - "classe": Apenas uma palavra: "Positivo", "Negativo" ou "Neutro".
    - "analise": Texto analisando o impacto das notícias recentes no valor intrínseco.
4. "perguntas_investigativas": Três perguntas cruciais que desafiem a tese de investimento, voltadas para o RI da empresa.

O tom deve ser técnico, direto e focado em preservação de capital.
"""
