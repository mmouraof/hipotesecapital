from datetime import datetime


def parse_numero(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".").replace("%",""))


def parse_data(data_str: str) -> str | None:
    if not data_str:
        return None
    data_str = data_str.strip()
    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
    ]
    for fmt in formatos:
        try:
            data = datetime.strptime(data_str, fmt)
            return data.strftime("%Y-%m-%d")  # padrão SQL
        except ValueError:
            continue