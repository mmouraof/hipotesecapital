"""Módulo de coleta de indicadores fundamentalistas via scraping e fallback GPT."""

import json
import logging
import os

from curl_cffi import requests
from bs4 import BeautifulSoup
from openai import OpenAI

logger = logging.getLogger(__name__)


def scrape_fundamentus(ticker: str) -> dict:
    """Coleta indicadores do Fundamentus via scraping HTML.

    Args:
        ticker: Código do ativo (ex: "PRIO3").

    Returns:
        Dicionário com todos os indicadores extraídos da página do Fundamentus.

    Raises:
        ValueError: Se nenhuma tabela de dados for encontrada para o ticker.
        requests.RequestException: Se a requisição HTTP falhar.
    """
    url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker.upper()}"
    response = requests.get(url, impersonate="chrome", timeout=15)
    response.encoding = "iso-8859-1"
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table", class_="w728")
    if not tables:
        raise ValueError(f"Nenhum dado encontrado para o ticker '{ticker}'")

    data = {}

    def clean(text: str) -> str:
        return text.replace("\xa0", " ").replace("?", "").strip()

    def parse_pairs(rows):
        """Extrai pares label/valor de linhas com 2 ou 4 colunas."""
        for row in rows:
            cells = [clean(td.get_text(strip=True)) for td in row.find_all("td")]
            if len(cells) >= 2:
                if cells[0]:
                    data[cells[0]] = cells[1]
            if len(cells) >= 4:
                if cells[2]:
                    data[cells[2]] = cells[3]
            if len(cells) >= 6:
                if cells[4]:
                    data[cells[4]] = cells[5]

    # Tabela 0: Papel, Cotação, Tipo, Empresa, Setor, Subsetor
    parse_pairs(tables[0].find_all("tr"))

    # Tabela 1: Valor de mercado, Valor da firma, Nro. Ações
    parse_pairs(tables[1].find_all("tr"))

    # Tabela 2: Oscilações + Indicadores fundamentalistas
    oscilacoes = {}
    rows = tables[2].find_all("tr")
    for row in rows[1:]:  # pula header
        cells = [clean(td.get_text(strip=True)) for td in row.find_all("td")]
        if len(cells) >= 2 and cells[0]:
            oscilacoes[cells[0]] = cells[1]
        if len(cells) >= 4 and cells[2]:
            data[cells[2]] = cells[3]
        if len(cells) >= 6 and cells[4]:
            data[cells[4]] = cells[5]
    data["Oscilações"] = oscilacoes

    # Tabela 3: Balanço Patrimonial
    parse_pairs(tables[3].find_all("tr")[1:])

    # Tabela 4: Demonstrativos de resultados
    dre_12m = {}
    dre_3m = {}
    rows = tables[4].find_all("tr")
    for row in rows[2:]:  # pula headers
        cells = [clean(td.get_text(strip=True)) for td in row.find_all("td")]
        if len(cells) >= 2 and cells[0]:
            dre_12m[cells[0]] = cells[1]
        if len(cells) >= 4 and cells[2]:
            dre_3m[cells[2]] = cells[3]
    data["DRE - Últimos 12 meses"] = dre_12m
    data["DRE - Últimos 3 meses"] = dre_3m

    return data


def scrape_investidor10(ticker: str) -> dict:
    """Coleta indicadores do Investidor10 via scraping HTML.

    Args:
        ticker: Código do ativo (ex: "PRIO3").

    Returns:
        Dicionário com indicadores extraídos da página do Investidor10.

    Raises:
        ValueError: Se nenhum indicador for encontrado para o ticker.
        requests.RequestException: Se a requisição HTTP falhar.
    """
    url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"
    response = requests.get(url, impersonate="chrome", timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data: dict = {}

    # Cards do topo: Cotação, Variação 12M, P/L, P/VP, DY
    for card in soup.find_all("div", class_="_card"):
        header = card.find(class_="_card-header")
        body = card.find(class_="_card-body")
        if header and body:
            label = header.get_text(strip=True)
            value = body.get_text(strip=True)
            if len(value) < 50:
                data[label] = value

    # Rentabilidade (oscilações)
    rent_section = soup.find(
        "div", string=lambda t: t and "rentabilidade" in t.lower() if t else False
    )
    if rent_section:
        parent = rent_section.find_parent()
        if parent:
            oscilacoes = {}
            for div in parent.find_all("div", recursive=False):
                period_label = div.find(
                    "div", class_=lambda c: c and "md:hidden" in " ".join(c) if c else False
                )
                if period_label:
                    full_text = div.get_text(strip=True)
                    label = period_label.get_text(strip=True)
                    value = full_text.replace(label, "", 1).strip()
                    if label and value:
                        oscilacoes[label] = value
            if oscilacoes:
                data["Rentabilidade"] = oscilacoes

    # Indicadores fundamentalistas (div.cell)
    indicadores = {}
    comparativos = {}
    for cell in soup.find_all("div", class_="cell"):
        label_span = cell.find(
            "span", class_=lambda c: c and "d-flex" in c if c else False
        )
        if not label_span:
            continue
        label = label_span.find(string=True, recursive=False)
        if label:
            label = label.strip().replace(f" - {ticker.upper()}", "")
        else:
            continue
        value_div = cell.find("div", class_="value")
        value = ""
        if value_div:
            val_span = value_div.find("span")
            if val_span:
                value = val_span.get_text(strip=True)
        if label and value:
            indicadores[label] = value
        sector_data = {}
        for s in cell.find_all("span", class_="sector-medias"):
            cat_text = s.find(string=True, recursive=False)
            destaque = s.find("span", class_="destaque")
            if cat_text and destaque:
                cat = cat_text.strip().rstrip(":")
                sector_data[cat] = destaque.get_text(strip=True)
        if sector_data:
            comparativos[label] = sector_data
    if indicadores:
        data["Indicadores"] = indicadores
    if comparativos:
        data["Comparativos"] = comparativos

    # Dividendos
    dividendos = []
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if thead and "data com" in thead.get_text().lower():
            tbody = table.find("tbody")
            for row in (tbody.find_all("tr") if tbody else []):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) >= 4:
                    dividendos.append({
                        "tipo": cells[0],
                        "data_com": cells[1],
                        "pagamento": cells[2],
                        "valor": cells[3],
                    })
            break
    data["Dividendos"] = dividendos

    # Informações da empresa
    info_empresa = {}
    for table in soup.find_all("table"):
        first_cell = table.find("td")
        if first_cell and "Nome da Empresa" in first_cell.get_text():
            for row in table.find_all("tr"):
                tds = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(tds) >= 2:
                    info_empresa[tds[0].rstrip(":")] = tds[1]
            break
    if info_empresa:
        data["Empresa"] = info_empresa

    if not data:
        raise ValueError(f"Nenhum dado encontrado para o ticker '{ticker}' no Investidor10")

    return data


def _coletar_via_gpt(ticker: str, nome_empresa: str) -> dict:
    """Fallback: coleta indicadores via GPT-4o com web search.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dicionário com indicadores extraídos pelo GPT.

    Raises:
        json.JSONDecodeError: Se a resposta não puder ser parseada como JSON.
        Exception: Para outros erros de API.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = (
        f"Busque em fontes como B3, Fundamentus, Status Invest e Yahoo Finance e extraia "
        f"os seguintes indicadores fundamentalistas de {nome_empresa} ({ticker}): "
        "cotação atual, data da última cotação, P/L, P/VP, Dividend Yield, ROE, ROIC, "
        "Margem Líquida, Margem EBIT, Dívida Líquida/EBITDA, EV/EBITDA, EV/EBIT, "
        "Receita Líquida (12m), Lucro Líquido (12m), EBITDA (12m), Dívida Bruta, "
        "Patrimônio Líquido, Ativo Total, Setor, Subsetor, Valor de Mercado, Nro. Ações. "
        "Use null apenas se o valor for confirmadamente indisponível em todas as fontes. "
        "Retorne SOMENTE um JSON puro (sem markdown, sem texto adicional) com exatamente "
        "estas chaves: \"Cotação\", \"Data últ cotação\", \"P/L\", \"P/VP\", "
        "\"Div.Yield\", \"ROE\", \"ROIC\", \"Mrg. Líq.\", \"Mrg. Ebit\", "
        "\"Dív.Líq./EBITDA\", \"EV/EBITDA\", \"EV/EBIT\", \"Receita Liq.\", "
        "\"Lucro Líquido\", \"EBITDA\", \"Dívida Bruta\", \"Patrim. Líq\", "
        "\"Ativo\", \"Setor\", \"Subsetor\", \"Valor de mercado\", \"Nro. Ações\"."
    )

    response = client.responses.create(
        model="gpt-4o",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
        max_output_tokens=1500,
    )

    texto = response.output_text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    return json.loads(texto)


def coletar_indicadores(ticker: str, nome_empresa: str) -> dict:
    """Coleta indicadores fundamentalistas de um ativo.

    Estratégia em três estágios:
    1. Scraping do Fundamentus (primário)
    2. Scraping do Investidor10 (fallback)
    3. GPT-4o com web search (último recurso, requer OPENAI_API_KEY)

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").

    Returns:
        Dicionário com os indicadores coletados. Retorna dict vazio se todos
        os métodos falharem.
    """
    try:
        logger.info("[%s] coletando via Fundamentus (scraping)", ticker)
        indicadores = scrape_fundamentus(ticker)
        logger.info("[%s] indicadores coletados via Fundamentus", ticker)
        return indicadores
    except Exception as e:
        logger.warning("[%s] Fundamentus falhou (%s) — tentando Investidor10", ticker, e)

    try:
        logger.info("[%s] coletando via Investidor10 (scraping)", ticker)
        indicadores = scrape_investidor10(ticker)
        logger.info("[%s] indicadores coletados via Investidor10", ticker)
        return indicadores
    except Exception as e:
        logger.warning("[%s] Investidor10 falhou (%s) — usando GPT fallback", ticker, e)

    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("[%s] OPENAI_API_KEY ausente — coleta encerrada sem dados", ticker)
        return {}

    try:
        indicadores = _coletar_via_gpt(ticker, nome_empresa)
        logger.info("[%s] indicadores coletados via GPT fallback", ticker)
        return indicadores
    except Exception as e:
        logger.warning("[%s] GPT fallback também falhou: %s", ticker, e)
        return {}
