from __future__ import annotations

import contextlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

_DC_NAMESPACE = "{http://purl.org/dc/elements/1.1/}"


@dataclass(frozen=True, slots=True)
class GeopoliticalFeed:
    """Configuration for a geopolitical RSS feed."""

    name: str
    url: str


@dataclass(frozen=True, slots=True)
class GeopoliticalArticle:
    """A geopolitical news article from RSS."""

    title: str
    link: str
    published: str
    source: str
    summary: str


GEOPOLITICAL_FEEDS: list[GeopoliticalFeed] = [
    GeopoliticalFeed(
        "Reuters World",
        "https://feeds.reuters.com/reuters/worldNews",
    ),
    GeopoliticalFeed(
        "AP World",
        "https://feeds.apnews.com/apf-topnews",
    ),
    GeopoliticalFeed(
        "BBC World",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ),
]


def fetch_geopolitical_feed(
    feed: GeopoliticalFeed,
) -> list[GeopoliticalArticle]:
    """Fetch and parse a geopolitical RSS feed."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(feed.url, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)  # noqa: S314
    articles: list[GeopoliticalArticle] = []
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        if not title:
            continue
        articles.append(
            GeopoliticalArticle(
                title=title,
                link=item.findtext("link", "").strip(),
                published=item.findtext("pubDate", "").strip(),
                source=feed.name,
                summary=item.findtext("description", "").strip(),
            ),
        )
    return articles


def fetch_all_geopolitical_feeds(
    feeds: list[GeopoliticalFeed] | None = None,
) -> list[GeopoliticalArticle]:
    """Fetch all geopolitical feeds, skipping errors."""
    target = feeds if feeds is not None else GEOPOLITICAL_FEEDS
    all_articles: list[GeopoliticalArticle] = []
    for feed in target:
        with contextlib.suppress(Exception):
            all_articles.extend(fetch_geopolitical_feed(feed))
    return all_articles
