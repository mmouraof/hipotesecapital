import urllib.parse
import urllib.request
from io import StringIO
import re
import unicodedata
from functools import lru_cache

import pandas as pd


FUNDAMENTUS_URL = "https://www.fundamentus.com.br/resultado.php"


def _to_float(value):
    # Converte formato brasileiro (com % opcional) para float padrão.
    if value is None:
        return None

    text = str(value).strip()
    if not text or text == "-":
        return None

    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1]

    text = text.replace(".", "").replace(",", ".")

    try:
        number = float(text)
        return number / 100 if is_percent else number
    except ValueError:
        return None


def _normalize_key(value):
    # Normaliza texto para comparação robusta de nomes de coluna.
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _get_by_alias(row, aliases):
    # Procura uma coluna pelo conjunto de aliases aceitos.
    normalized_map = {_normalize_key(col): col for col in row.index}
    for alias in aliases:
        normalized_alias = _normalize_key(alias)
        col_name = normalized_map.get(normalized_alias)
        if col_name is not None:
            return row.get(col_name)
    return None


@lru_cache(maxsize=1)
def _fetch_result_table():
    # Cacheia a tabela completa para evitar múltiplos downloads na mesma execução.
    payload = {
        "pl_min": "",
        "pl_max": "",
        "pvp_min": "",
        "pvp_max": "",
        "psr_min": "",
        "psr_max": "",
        "divy_min": "",
        "divy_max": "",
        "pativos_min": "",
        "pativos_max": "",
        "pcapgiro_min": "",
        "pcapgiro_max": "",
        "pebit_min": "",
        "pebit_max": "",
        "fgrah_min": "",
        "fgrah_max": "",
        "firma_ebit_min": "",
        "firma_ebit_max": "",
        "margemebit_min": "",
        "margemebit_max": "",
        "margemliq_min": "",
        "margemliq_max": "",
        "liqcorr_min": "",
        "liqcorr_max": "",
        "roic_min": "",
        "roic_max": "",
        "roe_min": "",
        "roe_max": "",
        "liq_min": "",
        "liq_max": "",
        "patrim_min": "",
        "patrim_max": "",
        "divbruta_min": "",
        "divbruta_max": "",
        "tx_cresc_rec_min": "",
        "tx_cresc_rec_max": "",
        "setor": "",
        "negociada": "ON",
        "ordem": "1",
        "x": "27",
        "y": "22",
    }

    encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url=FUNDAMENTUS_URL,
        data=encoded_data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html, text/plain, */*",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        html = response.read().decode("ISO-8859-1", errors="ignore")

    tables = pd.read_html(StringIO(html), attrs={"id": "resultado"})
    if not tables:
        return None
    return tables[0]


def get_fundamentus_info(ticker):
    # Retorna campos normalizados no padrão usado pelo dashboard/pipeline.
    try:
        table = _fetch_result_table()
        if table is None or table.empty:
            return {}

        table["Papel"] = table["Papel"].astype(str).str.upper().str.strip()
        match = table[table["Papel"] == str(ticker).upper().strip()]
        if match.empty:
            return {}

        row = match.iloc[0]

        return {
            "Nome": row.get("Empresa"),
            "P/L": _to_float(_get_by_alias(row, ["P/L", "pl"])),
            "ROE": _to_float(_get_by_alias(row, ["ROE", "roe"])),
            "DY": _to_float(_get_by_alias(row, ["DY", "div.yield", "divyield"])),
            "Margem Líquida": _to_float(_get_by_alias(row, ["Mrg. Líq.", "Mrg.Liq.", "Margem Líquida", "margemliq"])),
            "Dívida/Equity": _to_float(_get_by_alias(row, ["Dív.Brut/ Patrim.", "Div.Brut/Pat.", "Div.Brut/Patrim.", "DivBrutPatrim", "divbrutpat"])),
            "Preço Atual": _to_float(_get_by_alias(row, ["Cotação", "Cotacao", "Preço", "Preco"])),
            "Moeda": "BRL",
        }
    except Exception:
        return {}