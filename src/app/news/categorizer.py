from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.news.feeds import NewsArticle

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "apple", "microsoft", "google", "alphabet", "meta", "amazon",
        "nvidia", "semiconductor", "chip", "ai ", "artificial intelligence",
        "software", "tech", "technology", "nasdaq",
    ],
    "finance": [
        "bank", "jpmorgan", "goldman", "morgan stanley", "citigroup",
        "wells fargo", "interest rate", "fed ", "federal reserve",
        "financial", "lending", "credit",
    ],
    "energy": [
        "oil", "crude", "opec", "natural gas", "energy", "petroleum",
        "exxon", "chevron", "bp ", "shell ", "drilling",
    ],
    "healthcare": [
        "pharma", "biotech", "fda", "drug", "vaccine", "healthcare",
        "medical", "hospital", "clinical trial",
    ],
    "semiconductors": [
        "tsmc", "intel", "amd", "nvidia", "chip", "semiconductor",
        "foundry", "wafer", "fab ",
    ],
}

BULLISH_KEYWORDS: list[str] = [
    "rally", "surge", "gains", "record high", "bullish", "upgrade",
    "growth", "recovery", "beat expectations", "strong earnings",
    "expansion", "stimulus", "rate cut", "buyback", "outperform",
    "upbeat", "optimistic", "boom", "soar",
]

BEARISH_KEYWORDS: list[str] = [
    "crash", "plunge", "sell-off", "selloff", "recession", "bearish",
    "downgrade", "layoffs", "bankruptcy", "default", "tariff",
    "sanctions", "war", "inflation surge", "rate hike", "debt crisis",
    "decline", "slump", "tumble", "plummet", "warning", "crisis",
]


@dataclass(frozen=True, slots=True)
class CategorizedArticle:
    """An article with relevance scoring."""

    article: NewsArticle
    sectors: tuple[str, ...]
    sentiment: str
    relevance: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NewsSummary:
    """Aggregated news summary."""

    total_articles: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    sentiment: str
    top_articles: tuple[CategorizedArticle, ...]
    sector_mentions: dict[str, int]
    as_of: str


def _count_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    """Count keyword hits in text, return matched keywords."""
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]


def categorize_article(article: NewsArticle) -> CategorizedArticle:
    """Categorize an article by sentiment and sector."""
    text = f"{article.title} {article.summary}"

    # Detect sectors
    matched_sectors: list[str] = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in text.lower() for kw in keywords):
            matched_sectors.append(sector)

    # Detect sentiment
    bullish_hits = _count_keyword_hits(text, BULLISH_KEYWORDS)
    bearish_hits = _count_keyword_hits(text, BEARISH_KEYWORDS)

    if len(bullish_hits) > len(bearish_hits):
        sentiment = "BULLISH"
    elif len(bearish_hits) > len(bullish_hits):
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    # Relevance based on sector matches + keyword hits
    total_hits = len(bullish_hits) + len(bearish_hits)
    if matched_sectors and total_hits >= 2:
        relevance = "HIGH"
    elif matched_sectors or total_hits >= 1:
        relevance = "MEDIUM"
    else:
        relevance = "LOW"

    all_keywords = bullish_hits + bearish_hits
    return CategorizedArticle(
        article=article,
        sectors=tuple(matched_sectors),
        sentiment=sentiment,
        relevance=relevance,
        keywords=tuple(all_keywords),
    )


def build_news_summary(
    articles: list[CategorizedArticle],
    top_n: int = 5,
) -> NewsSummary:
    """Build an aggregated news summary from categorized articles."""
    bullish = sum(1 for a in articles if a.sentiment == "BULLISH")
    bearish = sum(1 for a in articles if a.sentiment == "BEARISH")
    neutral = len(articles) - bullish - bearish

    if bullish > bearish:
        overall = "BULLISH"
    elif bearish > bullish:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    # Count sector mentions
    sector_counts: dict[str, int] = {}
    for a in articles:
        for s in a.sectors:
            sector_counts[s] = sector_counts.get(s, 0) + 1

    # Top articles by relevance
    sorted_articles = sorted(
        articles,
        key=lambda a: (
            0 if a.relevance == "HIGH" else 1 if a.relevance == "MEDIUM" else 2
        ),
    )

    return NewsSummary(
        total_articles=len(articles),
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        sentiment=overall,
        top_articles=tuple(sorted_articles[:top_n]),
        sector_mentions=sector_counts,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
