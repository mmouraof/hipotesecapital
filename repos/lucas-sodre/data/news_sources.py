from urllib import error, parse, request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from data.yahoo_raw import get_news


def _dedupe_news(items, max_results):
    # Remove notícias repetidas usando título + link como chave.
    seen = set()
    unique_items = []

    for item in items:
        title = str(item.get("title", "")).strip().lower()
        link = str(item.get("link", "")).strip().lower()
        dedupe_key = (title, link)

        if not title and not link:
            continue
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        unique_items.append(item)

        if len(unique_items) >= max_results:
            break

    return unique_items


def _normalize_yahoo_items(yahoo_items):
    # Padroniza o formato do Yahoo para uma estrutura única do projeto.
    normalized = []

    for item in yahoo_items or []:
        content = item.get("content", item) if isinstance(item, dict) else {}
        if not isinstance(content, dict):
            continue

        provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
        click_info = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
        canonical_info = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}

        normalized.append(
            {
                "title": content.get("title") or item.get("title"),
                "publisher": content.get("publisher") or provider.get("displayName") or item.get("publisher"),
                "pubDate": content.get("pubDate") or content.get("displayTime") or content.get("providerPublishTime"),
                "link": content.get("link") or click_info.get("url") or canonical_info.get("url") or item.get("link"),
                "summary": content.get("summary") or content.get("description") or item.get("summary"),
            }
        )

    return normalized


def _parse_datetime(value):
    # Aceita múltiplos formatos de data (epoch, ISO e RSS).
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # Yahoo pode retornar epoch em segundos ou milissegundos.
        timestamp = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

        for fmt in (
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
        ):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


def _sort_by_recency(items):
    return sorted(
        items,
        key=lambda item: _parse_datetime(item.get("pubDate")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


def _filter_recent(items, recent_days):
    if recent_days is None:
        return items

    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
    filtered = []
    for item in items:
        published_at = _parse_datetime(item.get("pubDate"))
        if published_at and published_at >= cutoff:
            filtered.append(item)

    return filtered


def _google_news_rss(ticker, limit=10, recent_days=30):
    # Consulta RSS do Google News já com viés de recência.
    query = f"{ticker} B3 OR BOVESPA mercado financeiro when:{recent_days}d"
    encoded_query = parse.quote_plus(query)
    url = (
        "https://news.google.com/rss/search"
        f"?q={encoded_query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    req = request.Request(
        url=url,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            xml_content = response.read()
    except (error.URLError, error.HTTPError, TimeoutError):
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    items = []
    for entry in root.findall("./channel/item")[:limit]:
        title = entry.findtext("title")
        link = entry.findtext("link")
        pub_date = entry.findtext("pubDate")
        source_el = entry.find("source")
        publisher = source_el.text if source_el is not None else "Google News"

        items.append(
            {
                "title": title,
                "publisher": publisher,
                "pubDate": pub_date,
                "link": link,
                "summary": "",
            }
        )

    return items


def get_news_with_fallback(ticker, min_results=5, max_results=15):
    # Estratégia de fallback: Google RSS primeiro, Yahoo para complementar volume.
    google_news = _google_news_rss(ticker=ticker, limit=max_results, recent_days=30)
    merged_news = list(google_news)

    if len(merged_news) < min_results:
        yahoo_news = _normalize_yahoo_items(get_news(ticker) or [])
        merged_news.extend(yahoo_news)

    recent_news = _filter_recent(merged_news, recent_days=45)
    if recent_news:
        merged_news = recent_news

    # Prioriza notícias mais novas antes da deduplicação final.
    merged_news = _sort_by_recency(merged_news)

    return _dedupe_news(merged_news, max_results=max_results)