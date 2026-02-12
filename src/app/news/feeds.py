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
        "Yahoo Finance",
        "https://finance.yahoo.com/news/rssindex",
        "general",
    ),
    RSSFeed(
        "Bloomberg Markets",
        "https://feeds.bloomberg.com/markets/news.rss",
        "finance",
    ),
    RSSFeed(
        "MarketWatch",
        "https://www.marketwatch.com/rss/topstories",
        "general",
    ),
    RSSFeed(
        "WSJ Markets",
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "finance",
    ),
    RSSFeed(
        "WSJ Business",
        "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
        "general",
    ),
    RSSFeed(
        "Financial Times",
        "https://www.ft.com/markets?format=rss",
        "finance",
    ),
    RSSFeed(
        "Investing.com Stock Market",
        "https://www.investing.com/rss/news_25.rss",
        "general",
    ),
    RSSFeed(
        "Investing.com Economy",
        "https://www.investing.com/rss/news_14.rss",
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
        "CNBC Finance",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml"
        "?partnerId=wrss01&id=10000664",
        "finance",
    ),
]

_DC_NAMESPACE = "{http://purl.org/dc/elements/1.1/}"


def fetch_feed(feed: RSSFeed) -> list[NewsArticle]:
    """Fetch and parse an RSS feed into articles."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FinanceBot/1.0)"}
    with httpx.Client(timeout=10.0, headers=headers) as client:
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


def _dedup_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Remove duplicate articles by normalized title."""
    seen: set[str] = set()
    unique: list[NewsArticle] = []
    for article in articles:
        key = article.title.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(article)
    return unique


def fetch_all_feeds(
    feeds: list[RSSFeed] | None = None,
) -> list[NewsArticle]:
    """Fetch all configured feeds, skipping any that error."""
    target_feeds = feeds if feeds is not None else FINANCIAL_FEEDS
    all_articles: list[NewsArticle] = []
    for feed in target_feeds:
        with contextlib.suppress(Exception):
            all_articles.extend(fetch_feed(feed))
    return _dedup_articles(all_articles)
