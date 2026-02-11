from __future__ import annotations

import contextlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class RSSFeed:
    """Configuration for an RSS feed source."""

    name: str
    url: str
    category: str


@dataclass(frozen=True, slots=True)
class NewsArticle:
    """A parsed news article from an RSS feed."""

    title: str
    link: str
    published: str
    source: str
    summary: str
    author: str | None


FINANCIAL_FEEDS: list[RSSFeed] = [
    RSSFeed(
        "Reuters Business",
        "https://feeds.reuters.com/reuters/businessNews",
        "general",
    ),
    RSSFeed(
        "AP Business",
        "https://feeds.apnews.com/apf-business",
        "general",
    ),
    RSSFeed(
        "BBC Business",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "general",
    ),
    RSSFeed(
        "CNBC Top News",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=100003114",
        "general",
    ),
    RSSFeed(
        "CNBC Tech",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=19854910",
        "tech",
    ),
    RSSFeed(
        "CNBC Finance",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=10000664",
        "finance",
    ),
]

_DC_NAMESPACE = "{http://purl.org/dc/elements/1.1/}"


def fetch_feed(feed: RSSFeed) -> list[NewsArticle]:
    """Fetch and parse an RSS feed into articles."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(feed.url, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)  # noqa: S314
    articles: list[NewsArticle] = []
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "").strip()
        author = item.findtext("author") or item.findtext(
            f"{_DC_NAMESPACE}creator",
        )
        if author:
            author = author.strip()
        if title:
            articles.append(
                NewsArticle(
                    title=title,
                    link=link,
                    published=pub_date,
                    source=feed.name,
                    summary=desc,
                    author=author,
                ),
            )
    return articles


def fetch_all_feeds(
    feeds: list[RSSFeed] | None = None,
) -> list[NewsArticle]:
    """Fetch all configured feeds, skipping any that error."""
    target_feeds = feeds if feeds is not None else FINANCIAL_FEEDS
    all_articles: list[NewsArticle] = []
    for feed in target_feeds:
        with contextlib.suppress(Exception):
            all_articles.extend(fetch_feed(feed))
    return all_articles
