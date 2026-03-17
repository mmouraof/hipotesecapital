"""Módulo de coleta de notícias via RSS do Google News."""

import logging
from datetime import datetime
from urllib.parse import quote

import feedparser

logger = logging.getLogger(__name__)


def coletar_noticias(
    ticker: str, nome_empresa: str, max_noticias: int = 5
) -> list[dict]:
    """Coleta notícias recentes de um ativo via RSS do Google News.

    Busca por ticker e nome da empresa nos últimos 7 dias, retornando as
    notícias mais recentes primeiro.

    Args:
        ticker: Código do ativo (ex: "PRIO3").
        nome_empresa: Nome da empresa (ex: "PRIO").
        max_noticias: Número máximo de notícias a retornar. Default: 5.

    Returns:
        Lista de dicts com as chaves: titulo, link, data_publicacao, fonte.
        Retorna lista vazia se o feed falhar ou não tiver entradas.
    """
    query = quote(f'{ticker} OR "{nome_empresa}" when:7d')
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    try:
        feed = feedparser.parse(url)

        if not feed.entries:
            logger.warning("Feed vazio para %s (%s)", ticker, nome_empresa)
            return []

        noticias = []
        for entry in feed.entries:
            data_pub = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                data_pub = datetime(*entry.published_parsed[:6]).isoformat()

            fonte = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                fonte = entry.source.title
            elif hasattr(entry, "tags") and entry.tags:
                fonte = entry.tags[0].get("term", "")

            noticias.append(
                {
                    "titulo": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "data_publicacao": data_pub,
                    "fonte": fonte,
                }
            )

        # Ordena por data decrescente (None vai para o fim)
        noticias.sort(key=lambda n: n["data_publicacao"] or "", reverse=True)

        logger.info("%d notícias coletadas para %s", len(noticias[:max_noticias]), ticker)
        return noticias[:max_noticias]

    except Exception as e:
        logger.warning("Erro ao coletar notícias de %s: %s", ticker, e)
        return []
