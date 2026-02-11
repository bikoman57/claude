from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.social.sentiment import classify_sentiment, extract_tickers

TRACKED_SUBREDDITS: list[str] = ["wallstreetbets", "stocks", "investing"]

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"  # noqa: S105
_API_BASE = "https://oauth.reddit.com"
_USER_AGENT = "fin-agents/0.1.0"


@dataclass(frozen=True, slots=True)
class RedditPost:
    """A Reddit post with sentiment data."""

    subreddit: str
    title: str
    score: int
    num_comments: int
    url: str
    created_utc: str
    sentiment: str
    tickers_mentioned: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SubredditSentiment:
    """Aggregated sentiment for a subreddit."""

    subreddit: str
    total_posts: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    sentiment: str
    trending_tickers: tuple[str, ...]
    unusual_activity: bool


@dataclass(frozen=True, slots=True)
class RedditSummary:
    """Combined Reddit sentiment summary."""

    subreddits: tuple[SubredditSentiment, ...]
    overall_sentiment: str
    top_tickers: tuple[str, ...]
    as_of: str


def _get_reddit_token() -> str | None:
    """Get OAuth token using client credentials. Returns None if not configured."""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            _TOKEN_URL,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()

    data = resp.json()
    return data.get("access_token")  # type: ignore[no-any-return]


def fetch_subreddit_posts(
    subreddit: str,
    token: str,
    limit: int = 25,
) -> list[RedditPost]:
    """Fetch hot posts from a subreddit."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{_API_BASE}/r/{subreddit}/hot",
            params={"limit": str(limit)},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": _USER_AGENT,
            },
        )
        resp.raise_for_status()

    data = resp.json()
    posts: list[RedditPost] = []
    for child in data.get("data", {}).get("children", []):
        post_data = child.get("data", {})
        title = post_data.get("title", "")
        if not title:
            continue
        posts.append(
            RedditPost(
                subreddit=subreddit,
                title=title,
                score=int(post_data.get("score", 0)),
                num_comments=int(post_data.get("num_comments", 0)),
                url=post_data.get("url", ""),
                created_utc=str(post_data.get("created_utc", "")),
                sentiment=classify_sentiment(title),
                tickers_mentioned=tuple(extract_tickers(title)),
            ),
        )
    return posts


def _aggregate_subreddit(
    subreddit: str,
    posts: list[RedditPost],
) -> SubredditSentiment:
    """Aggregate sentiment for one subreddit."""
    bullish = sum(1 for p in posts if p.sentiment == "BULLISH")
    bearish = sum(1 for p in posts if p.sentiment == "BEARISH")
    neutral = len(posts) - bullish - bearish

    if bullish > bearish:
        sentiment = "BULLISH"
    elif bearish > bullish:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    # Trending tickers by mention frequency
    ticker_counts: dict[str, int] = {}
    for p in posts:
        for t in p.tickers_mentioned:
            ticker_counts[t] = ticker_counts.get(t, 0) + 1
    trending = sorted(ticker_counts, key=ticker_counts.get, reverse=True)[:5]  # type: ignore[arg-type]

    # Unusual activity: high avg comments or score
    avg_score = sum(p.score for p in posts) / max(len(posts), 1)
    unusual = avg_score > 1000

    return SubredditSentiment(
        subreddit=subreddit,
        total_posts=len(posts),
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        sentiment=sentiment,
        trending_tickers=tuple(trending),
        unusual_activity=unusual,
    )


def fetch_reddit_summary() -> RedditSummary | None:
    """Fetch Reddit summary. Returns None if credentials not configured."""
    token = _get_reddit_token()
    if token is None:
        return None

    subreddit_results: list[SubredditSentiment] = []
    all_ticker_counts: dict[str, int] = {}

    for sub in TRACKED_SUBREDDITS:
        posts = fetch_subreddit_posts(sub, token)
        agg = _aggregate_subreddit(sub, posts)
        subreddit_results.append(agg)
        for t in agg.trending_tickers:
            all_ticker_counts[t] = all_ticker_counts.get(t, 0) + 1

    bullish_total = sum(s.bullish_count for s in subreddit_results)
    bearish_total = sum(s.bearish_count for s in subreddit_results)
    if bullish_total > bearish_total:
        overall = "BULLISH"
    elif bearish_total > bullish_total:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    top = sorted(all_ticker_counts, key=all_ticker_counts.get, reverse=True)[:10]  # type: ignore[arg-type]

    return RedditSummary(
        subreddits=tuple(subreddit_results),
        overall_sentiment=overall,
        top_tickers=tuple(top),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
