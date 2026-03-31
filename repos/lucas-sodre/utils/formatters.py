import pandas as pd


def format_text(value, fallback="-"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def format_number(value, decimals=2, fallback="-"):
    if value is None or pd.isna(value):
        return fallback
    return f"{value:.{decimals}f}"


def format_currency(value, currency="BRL", fallback="-"):
    if value is None or pd.isna(value):
        return fallback
    return f"{value:,.2f} {currency}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value, decimals=2, fallback="-"):
    if value is None or pd.isna(value):
        return fallback
    return f"{value * 100:.{decimals}f}%"


def format_news_datetime(timestamp):
    if timestamp is None or pd.isna(timestamp):
        return "Data indisponivel"

    if isinstance(timestamp, str):
        try:
            return pd.to_datetime(timestamp, errors="raise").strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return "Data indisponivel"

    try:
        return pd.to_datetime(timestamp, unit="s").strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        try:
            return pd.to_datetime(timestamp, unit="ms").strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return "Data indisponivel"