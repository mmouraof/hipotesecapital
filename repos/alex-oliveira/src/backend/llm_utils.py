import anthropic
from  google import genai
from weasyprint import HTML
from dotenv import load_dotenv
import os
import json



load_dotenv()



def generate_ai_resume(ticker: str, text: str) -> str:
    """
    Gera um resumo de algum texto relacionado a um ticker utilizando o Gemini.

    Args:
        ticker: Código do ativo (ex: 'PETR4.SA', 'AAPL')
        text: Texto referente ao ticker

    Returns:
        Texto resumido com pontos pertinentes ao ticker
    """

    # Instancia o cliente
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # System Instruction
    system_instruction = (
        f"Você é um motor de sumarização purista para análise de equity ({ticker}). "
        "Sua saída deve conter exclusivamente o resumo textual, sem saudações, "
        "sem metadados e sem formatação de lista."
    )

    # Prompt de Conteúdo
    user_content = f"""
    Sintetize o texto abaixo focando estritamente em eventos corporativos, dinâmicas de setor ou fatos relevantes para o ticker {ticker}.

    REGRAS CRÍTICAS DE NEGÓCIO:
    1. FORMATO: Máximo de 2 parágrafos de prosa contínua. Proibido o uso de '-' ou '*' ou qualquer tipo de lista.
    2. FILTRO DE RUÍDO: Ignore sistematicamente: datas de fundação, biografias de executivos, valores de faturamento passados, lucro histórico ou descrições genéricas da empresa.
    3. FOCO: Priorize o "porquê" da notícia (ex: mudança de estratégia, impacto regulatório, nova parceria) em vez do "quem".
    4. INTEGRIDADE: Se o texto for contraditório, use apenas os fatos concretos e omita opiniões de colunistas.
    5. LINGUAGEM: Use terminologia de mercado financeiro (ex: 'market share', 'bottom-line', 'guidance', 'capex') de forma concisa.

    TEXTO BRUTO PARA PROCESSAMENTO:
    {text}
    """

    # Configuração do agente
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config={
            "system_instruction": system_instruction,
            "temperature": 0.1,
            "top_p": 0.95,
        },
        contents=user_content
    )

    return response.text



def generate_ai_news_report(ticker: str, link: str) -> dict:

    """
    Gera um relatório completo de 5 notícias sobre o ticker com Gemini

    Args:
        ticker: Código do ativo (ex: 'PETR4.SA', 'AAPL')
        Link da notícia

    Returns:
        Análise estruturada com o seguinte dicionário:
        {"link", "resumo", "classificação": NEGATIVO, NEUTRO ou POSITIVO, "escala": -1 a 1}
    """

    # Instancia o cliente
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # System Instruction
    system_instruction = (
        f"Você é um Analista de Equity especializado em {ticker}. "
        "Sua tarefa é processar notícias brutas e retornar uma análise estruturada em JSON. "
        "Não inclua nenhuma explicação fora do objeto JSON."
    )

    # Prompt de Conteúdo
    user_content = f"""
    Analise o conteúdo sobre {ticker} e preencha o seguinte objeto JSON:
    
    ESQUEMA ESPERADO:
    {{
        "link": {link}
        "resumo": "Texto de 1 a 2 parágrafos técnicos e fluidos, sem bullet points.",
        "classificacao": "POSITIVO, NEUTRO ou NEGATIVO",
        "escala": <float entre -1.0 e 1.0, em que -1.0 representa impacto 
                extremamente negativo no preço da ação, 0.0 representa 
                neutralidade e 1.0 representa impacto extremamente positivo 
                no preço da ação>
    }}

    CONTEÚDO PARA ANALISAR:
    {link}
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config={
            "system_instruction": system_instruction,
            "temperature": 0.1,
            "response_mime_type": "application/json"
        },
        contents=user_content
    )

    # Converte a string JSON em um dicionário
    try:
        dados_processados = json.loads(response.text)
        return dados_processados
    except json.JSONDecodeError:
        return {"erro": "Falha ao processar resposta da IA", "raw": response.text}



def ai_translater(texto: str, idioma_destino: str = "protuguês brasileiro") -> str:

    """
    Traduz um texto para determinado idioma com Claude

    Args:
        Texto para ser traduzido
        Idioma de tradução

    Returns:
        Texto traduzido
    """

    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    PROMPT = f"""
    Você é um tradutor profissional especializado.

    Traduza o texto abaixo para o {idioma_destino}.

    REGRAS:
    - Retorne APENAS o texto traduzido, sem explicações, comentários ou texto adicional
    - Preserve a formatação original (quebras de linha, marcadores, etc.)
    - Mantenha termos técnicos reconhecidos internacionalmente no idioma original quando apropriado
    - Seja fiel ao tom e estilo do texto original

    TEXTO:
    {texto}
    """

    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8096,
        messages=[{"role": "user", "content": PROMPT}]
    )

    return msg.content[0].text



def generate_ai_report(dados: dict) -> str:

    """
    Gera um relatório detalhado sobre dados de um ticker

    Args:
        Dicionário de dados com dados cadastrais, dados de cotação, indicadores fundamentalistas e resumo de notícias

    Returns:
        HTML com o relatório estruturado
    """

    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    PROMPT = f"""
    Você é um analista fundamentalista sênior de renda variável brasileiro.

    Com base nos dados abaixo, gere um relatório de análise fundamentalista completo em HTML,
    pronto para impressão em PDF. Seja técnico, objetivo e profissional.

    DADOS DA EMPRESA:
    {json.dumps(dados, ensure_ascii=False, indent=2)}

    ESTRUTURA OBRIGATÓRIA DO RELATÓRIO (em ordem):

    1. CABEÇALHO
    - Logo fictício da empresa (use as iniciais do ticker em um círculo azul escuro)
    - Nome da empresa, ticker, setor e segmento (classificação B3)
    - Data de geração do relatório

    2. DADOS CADASTRAIS
    - Nome, setor, segmento, país
    - Descrição resumida do modelo de negócio (baseada na descrição fornecida, em 3-4 linhas)

    3. DADOS DE MERCADO
    - Preço atual, variação 6 meses, mínima/máxima 6 meses, market cap
    - Tabela com os 5 indicadores fundamentalistas formatados

    4. INTERPRETAÇÃO DOS INDICADORES
    - Para cada indicador (P/L, ROE, Margem Líquida, Dividend Yield, Dívida/EBITDA):
        explique O QUE O NÚMERO SUGERE sobre a empresa, se está acima/abaixo da média
        do setor e o que isso implica para o investidor. Use linguagem analítica.

    5. SÍNTESE DAS NOTÍCIAS
    - Liste cada notícia com título e URL clicável
    - Classifique cada uma como 🟢 Positiva, 🔴 Negativa ou 🟡 Neutra
    - Escreva 1-2 linhas de análise para cada notícia
    - Síntese geral do sentimento de mercado

    6. TRÊS PERGUNTAS DO ANALISTA
    - Três perguntas críticas e específicas (baseadas nos dados reais)
        que um analista deveria investigar antes de tomar decisão de investimento

    7. RODAPÉ
    - Aviso legal: "Este relatório foi gerado com auxílio de IA e não constitui recomendação de investimento."
    - Data e hora de geração

    REGRAS DE FORMATAÇÃO:
    - Gere APENAS o HTML completo (<!DOCTYPE html> até </html>), sem texto antes ou depois
    - CSS inline completo, sem dependências externas (sem Google Fonts, sem CDN)
    - Paleta: azul escuro (#1a2e4a), azul médio (#2e5090), branco (#ffffff), cinza claro (#f4f6f9), verde (#27ae60), vermelho (#e74c3c), amarelo (#f39c12)
    - Fonte: Arial, Helvetica, sans-serif
    - Margens adequadas para impressão: @media print com margin de 1.5cm
    - Cards com sombra sutil para KPIs
    - Tabelas com cabeçalho em azul escuro e linhas alternadas
    - Divisores horizontais entre seções
    - Evite page-break dentro de seções importantes no @media print
    """

    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8096,
        messages=[{"role": "user", "content": PROMPT}]
    )

    html = msg.content[0].text.strip()

    # Limpa possíveis marcações de código
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
    if html.endswith("```"):
        html = html.rsplit("```", 1)[0]

    return html.strip()



def pdf_report_saver(html: str, nome_arquivo: str) -> None:

    """
    Função que salva um HTML para um PDF

    Args:
        "Link" do HTML
        Nome do arquivo que gostaria de salvar

    Returns:
        None
    """

    HTML(string=html).write_pdf(nome_arquivo)