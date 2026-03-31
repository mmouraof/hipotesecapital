import requests
from bs4 import BeautifulSoup


def get_all_tickers():
    """Esta função retorna uma lista de todos
    os tickers na B3 com base no site da Infomoney"""

    url = "https://www.dadosdemercado.com.br/acoes"

    # Usa timeout e User-Agent para reduzir bloqueios da requisição.
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    html = response.text

    soup = BeautifulSoup(html, "html.parser")
    tickers = []

    # A tabela principal de ações fica no id "stocks".
    table = soup.find("table", id="stocks")
    if table is None:
        return []

    tds = table.find_all("strong")

    for td in tds:
        a = td.find("a")
        if a and a.text:
            # Normaliza para o padrão usado no restante do pipeline.
            tickers.append(a.text.strip().upper())

    # Remove duplicados preservando ordem.
    return list(dict.fromkeys(tickers))
        
    

