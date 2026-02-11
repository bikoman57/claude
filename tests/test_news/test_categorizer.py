from __future__ import annotations

from app.news.categorizer import (
    build_news_summary,
    categorize_article,
)
from app.news.feeds import NewsArticle


def _article(title: str, summary: str = "") -> NewsArticle:
    return NewsArticle(
        title=title,
        link="https://example.com",
        published="2026-02-10",
        source="Test",
        summary=summary,
        author=None,
    )


def test_bullish_sentiment():
    a = _article("Markets rally on strong earnings")
    ca = categorize_article(a)
    assert ca.sentiment == "BULLISH"
    assert "rally" in ca.keywords


def test_bearish_sentiment():
    a = _article("Stocks crash amid recession fears")
    ca = categorize_article(a)
    assert ca.sentiment == "BEARISH"
    assert "crash" in ca.keywords


def test_neutral_sentiment():
    a = _article("Company announces new product line")
    ca = categorize_article(a)
    assert ca.sentiment == "NEUTRAL"


def test_sector_detection_tech():
    a = _article("Nvidia announces new AI chip")
    ca = categorize_article(a)
    assert "tech" in ca.sectors or "semiconductors" in ca.sectors


def test_sector_detection_energy():
    a = _article("Oil prices fall as OPEC increases supply")
    ca = categorize_article(a)
    assert "energy" in ca.sectors


def test_sector_detection_finance():
    a = _article("Federal Reserve raises interest rate")
    ca = categorize_article(a)
    assert "finance" in ca.sectors


def test_high_relevance():
    a = _article(
        "Tech stocks surge after Nvidia earnings beat expectations",
    )
    ca = categorize_article(a)
    assert ca.relevance == "HIGH"


def test_low_relevance():
    a = _article("Local weather update for today")
    ca = categorize_article(a)
    assert ca.relevance == "LOW"


def test_build_news_summary_aggregation():
    articles = [
        categorize_article(_article("Markets rally on growth")),
        categorize_article(_article("Stocks crash in sell-off")),
        categorize_article(_article("Company hires new CEO")),
    ]
    summary = build_news_summary(articles)
    assert summary.total_articles == 3
    assert summary.bullish_count == 1
    assert summary.bearish_count == 1
    assert summary.neutral_count == 1
    assert summary.sentiment == "NEUTRAL"


def test_build_news_summary_bearish_majority():
    articles = [
        categorize_article(_article("Stocks crash")),
        categorize_article(_article("Markets plunge on crisis")),
        categorize_article(_article("Markets rally")),
    ]
    summary = build_news_summary(articles)
    assert summary.sentiment == "BEARISH"
    assert summary.bearish_count == 2


def test_build_news_summary_top_n():
    articles = [
        categorize_article(_article("A")),
        categorize_article(_article("B")),
        categorize_article(_article("C")),
    ]
    summary = build_news_summary(articles, top_n=2)
    assert len(summary.top_articles) == 2
