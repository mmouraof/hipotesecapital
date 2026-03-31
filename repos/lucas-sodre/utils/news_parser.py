from utils.formatters import format_news_datetime, format_text


def extract_news_item(item):
    content = item.get("content", item) or {}

    title = content.get("title") or item.get("title")
    provider_info = content.get("provider") if isinstance(content.get("provider"), dict) else {}
    publisher = (
        content.get("publisher")
        or provider_info.get("displayName")
        or item.get("publisher")
    )

    published_at = (
        content.get("providerPublishTime")
        or content.get("pubDate")
        or content.get("displayTime")
        or item.get("providerPublishTime")
        or item.get("pubDate")
    )

    click_info = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    canonical_info = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    link = (
        content.get("link")
        or click_info.get("url")
        or canonical_info.get("url")
        or item.get("link")
    )

    return {
        "title": format_text(title, "Sem título"),
        "publisher": format_text(publisher, "Fonte indisponível"),
        "published_at": format_news_datetime(published_at),
        "link": link,
        "summary": format_text(content.get("summary") or content.get("description"), "Resumo indisponível"),
    }