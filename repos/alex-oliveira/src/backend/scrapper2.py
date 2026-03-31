from bs4 import BeautifulSoup
import requests
import time
from dotenv import load_dotenv
import numpy as np

from src.utils import *
from src.backend.llm_utils import *


load_dotenv()


# Dados cadastrais usando o site Status Invest, Investidor 10 e um resumo usando Gemini
def get_register_data(ticker, max_tries, sleep):
    
    # URLs usadas
    url_status = f"https://statusinvest.com.br/acoes/{ticker.lower()}"
    url_investidor_10 = f"https://investidor10.com.br/acoes/{ticker.lower()}"

    # Verificações básicas de conexão
    for i in range(max_tries):
        print(f"Tentativa {i+1}")
        response1 = requests.get(url_status)
        response2 = requests.get(url_investidor_10)
        if response1.status_code != 200 or response2.status_code != 200:
            print(f"Não conseguimos acessar a Status Invest ou a Investidor 10. Verifique o nome do ticker ou a conexão. Status: {response1.status_code} e {response2.status_code}")
            time.sleep(sleep)
            if i == max_tries - 1:
                return None
        else:
            print("Conexão garantida")
            break
    
    # Criando instâncias para webscrapping
    soup_status = BeautifulSoup(response1.text, "html.parser")
    investidor_10 = BeautifulSoup(response2.text, "html.parser")

    # Dados
    data = {}

    # Nome da empresa
    nome = soup_status.find("span", class_='d-block fw-600 text-main-green-dark')        

    # Setor e Segmento
    atuacao = soup_status.find("div", class_='top-info top-info-1 top-info-sm-2 top-info-md-n sm d-flex justify-between')
    atuacao = atuacao.find_all("strong", class_='value')
    setor_atuacao = atuacao[0]
    segmento_atuacao = atuacao[2]

    # Modelo de negócio
    resumo_negocio = investidor_10.find("div", id="about-company")
    resumo_negocio = resumo_negocio.find("div", class_="text-content")

    # Frase de não encontrado
    nao_encontrado = "Não encontrado(a)"

    # Preenchendo os dados
    if nome:
        data["nome_empresa"] = nome.text.strip()
    else:
        data["nome_empresa"] = nao_encontrado

    if setor_atuacao:
        data["setor"] = setor_atuacao.text.strip()
    else:
        data["setor"] = nao_encontrado

    if segmento_atuacao:
        data["segmento"] = segmento_atuacao.text.strip()
    else:
        data["segmento"] = nao_encontrado

    if resumo_negocio:
        resumo_negocio = resumo_negocio.text.strip()
        data["resumo_negocio"] = generate_ai_resume(ticker, resumo_negocio) # Resumo com AI
    else:
        data["resumo_negocio"] = nao_encontrado

    # Retornando
    return data



# Dados de cotação usando os sites Fundamentus
def get_cotation_data(ticker, max_tries, sleep):

    # URL usada
    url_fundamentus = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker.upper()}"

    # Verificações bássicas de conexão
    for i in range(max_tries):
        print(f"Tentativa {i+1}")
        response = requests.get(url_fundamentus)
        if response.status_code != 200:
            print(f"Não conseguimos acessar a Fundamentus. Verifique o nome do ticker ou a conexão. Status: {response.status_code}")
            time.sleep(sleep)
            if i == max_tries - 1:
                return None
        else:
            print("Conexão garantida")
            break
    
    # Criando a instância para o web scrapping
    soup_fundamentus = BeautifulSoup(response.text, "html.parser")

    # Dados
    data = {}

    # Fiz essa separação pois há duas tabelas com os dados de cotação no site Fundamentos
    dados_cotacao = soup_fundamentus.find_all("table", class_="w728")
    dados_cotacao1 = dados_cotacao[0].find_all("span", class_="txt")
    dados_cotacao2 = dados_cotacao[1].find_all("span", class_="txt")

    # Dados de cotação
    cotacao = dados_cotacao1[3].text.strip()
    data_ultima_cotacao = dados_cotacao1[7].text.strip()
    min_52_sem = dados_cotacao1[11].text.strip()
    max_52_sem = dados_cotacao1[15].text.strip()
    volume_medio_negociacao_2_meses = dados_cotacao1[19].text.strip()
    valor_mercado = dados_cotacao2[1].text.strip()
    ult_balanco_process = dados_cotacao2[3].text.strip()
    num_acoes = dados_cotacao2[7].text.strip()

    # Frase de não encontrado
    nao_encontrado = "Não encontrado(a)"

    # Preenchendo os dados
    if cotacao:
        data["cotacao"] = parse_numero(cotacao)
    else:
        data["cotacao"] = nao_encontrado

    if data_ultima_cotacao:
        data["data_ultima_cotacao"] = parse_data(data_ultima_cotacao)
    else:
        data["data_ultima_cotacao"] = nao_encontrado

    if min_52_sem:
        data["minimo_52_semanas"] = parse_numero(min_52_sem)
    else:
        data["minimo_52_semanas"] = nao_encontrado

    if max_52_sem:
        data["maximo_52_semanas"] = parse_numero(max_52_sem)
    else:
        data["maximo_52_semanas"] = nao_encontrado

    if volume_medio_negociacao_2_meses:
        data["volume_medio_2_meses"] = parse_numero(volume_medio_negociacao_2_meses)
    else:
        data["volume_medio_2_meses"] = nao_encontrado
    
    if valor_mercado:
        data["valor_de_mercado"] = parse_numero(valor_mercado)
    else:
        data["valor_de_mercado"] = nao_encontrado

    if ult_balanco_process:
        data["data_ultimo_balanco"] = parse_data(ult_balanco_process)
    else:
        data["data_ultimo_balanco"] = nao_encontrado

    if num_acoes:
        data["numero_de_acoes"] = parse_numero(num_acoes)
    else:
        data["numero_de_acoes"] = nao_encontrado
    
    # Retornando
    return data



# Indicadores fundamentalistas usando Investidor 10
def get_fundamentalist_data(ticker, max_tries, sleep):

    # URL usada
    url_investidor = f"https://investidor10.com.br/acoes/{ticker.lower()}/"

    # Verificações bássicas de conexão
    for i in range(max_tries):
        print(f"Tentativa {i+1}")
        response = requests.get(url_investidor)
        if response.status_code != 200:
            print(f"Não conseguimos acessar a Fundamentus. Verifique o nome do ticker ou a conexão. Status: {response.status_code}")
            time.sleep(sleep)
            if i == max_tries - 1:
                return None
        else:
            print("Conexão garantida")
            break
    
    # Criando a instância para o web scrapping
    soup_investidor = BeautifulSoup(response.text, "html.parser")
    indicadores_fundamentalistas = soup_investidor.find("div", id="table-indicators", class_="table table-bordered outter-borderless")
    indicadores_fundamentalistas = indicadores_fundamentalistas.find_all("div", class_="value d-flex justify-content-between align-items-center")

    # Dados
    data = {}

    # Indicadores fundamentalistas
    p_por_l = indicadores_fundamentalistas[0].text.strip()
    dividend_yield = indicadores_fundamentalistas[3].text.strip()
    margem_liquida = indicadores_fundamentalistas[5].text.strip()
    roe = indicadores_fundamentalistas[19].text.strip()
    divida_liquida_por_ebitda = indicadores_fundamentalistas[23].text.strip()

    # Frase de não encontrado
    nao_encontrado = "Não encontrado(a)"

    # Preenchendo os dados
    if p_por_l:
        data["p_l"] = parse_numero(p_por_l)
    else:
        data["p_l"] = nao_encontrado

    if roe:
        data["roe"] = parse_numero(roe)/100
    else:
        data["roe"] = nao_encontrado

    if divida_liquida_por_ebitda:
        data["divida_liquida_ebtida"] = parse_numero(divida_liquida_por_ebitda)
    else:
        data["divida_liquida_ebtida"] = nao_encontrado

    if margem_liquida:
        data["margem_liquida"] = parse_numero(margem_liquida)/100
    else:
        data["margem_liquida"] = nao_encontrado

    if dividend_yield:
        data["dividend_yield"] = parse_numero(dividend_yield)/100
    else:
        data["dividend_yield"] = nao_encontrado

    # Retornando
    return data



# Notícias com a API Trading View e resumo com IA
def get_news_data(ticker, max_tries, sleep):

    # URL usada
    url_trading = f"https://news-mediator.tradingview.com/public/view/v1/symbol?filter=lang%3Apt&filter=symbol%3ABMFBOVESPA%3A{ticker.upper()}&client=landing&streaming=false&user_prostatus=non_pr"

    # Verificações bássicas de conexão
    for i in range(max_tries):
        print(f"Tentativa {i+1}")
        response = requests.get(url_trading)
        if response.status_code != 200:
            print(f"Não conseguimos acessar a API de notícias do Trading View. Verifique o nome do ticker ou a conexão. Status: {response.status_code}")
            time.sleep(sleep)
            if i == max_tries - 1:
                return None
        else:
            print("Conexão garantida")
            break
    
    # Resposta do json
    todas_noticias = response.json()["items"]

    # Dados
    data = {}

    # Pegando 5 notícias
    noticias = np.random.choice(todas_noticias, size=5)

    # Fazendo um resumo e classificando cada uma delas
    for i in range(1):
        if noticias[i]["storyPath"]:
            url_noticia = "https://br.tradingview.com" + noticias[i]["storyPath"]
            _, resumo, classificador, escala = generate_ai_news_report(ticker, url_noticia)
            data[f"noticia_{i+1}"] = [url_noticia, resumo, classificador, escala]
        else:
            data[f"noticia_{i+1}"] = "Não encontrado(a)"

    # Retornando
    return data


# Gerando todos os dados
def get_full_data(ticker, max_tries, sleep):

    """
    Coleta dados cadastrais, de cotação e fundamentalistas de uma ação via yfinance.

    Args:
        ticker: Código do ativo (ex: 'PETR4.SA', 'AAPL')

    Returns:
        Dicionário com todas as informações coletadas.
    """
        
    data = {}

    cadastro_data = get_register_data(ticker, max_tries, sleep)
    cotacao_data = get_cotation_data(ticker, max_tries, sleep)
    fundamentalista_data = get_fundamentalist_data(ticker, max_tries, sleep)
    noticia_data = get_news_data(ticker, max_tries, sleep)

    data["ticker"] = ticker.upper()
    data["data_coleta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["dados_cadastrais"] = cadastro_data
    data["dados_cotacao"] = cotacao_data
    data["indicadores_fundamentalistas"] = fundamentalista_data
    data["noticias"] = noticia_data

    return data


# Exemplo
# if __name__ == "__main__":
#     print(get_full_data("recv3", 5, 0))