from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.social.reddit import (
    _aggregate_subreddit,
    fetch_reddit_summary,
    fetch_subreddit_posts,
)

_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "$AAPL to the moon! Rally incoming!",
                    "score": 500,
                    "num_comments": 200,
                    "url": "https://reddit.com/1",
                    "created_utc": 1707580800,
                },
            },
            {
                "data": {
                    "title": "Market crash imminent, puts on $SPY",
                    "score": 300,
                    "num_comments": 150,
                    "url": "https://reddit.com/2",
                    "created_utc": 1707577200,
                },
            },
            {
                "data": {
                    "title": "What do you think about earnings?",
                    "score": 50,
                    "num_comments": 10,
                    "url": "https://reddit.com/3",
                    "created_utc": 1707573600,
                },
            },
        ],
    },
}


@patch("app.social.reddit.httpx.Client")
def test_fetch_subreddit_posts(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _REDDIT_RESPONSE
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    posts = fetch_subreddit_posts("wallstreetbets", "fake-token")
    assert len(posts) == 3
    assert posts[0].sentiment == "BULLISH"
    assert "AAPL" in posts[0].tickers_mentioned
    assert posts[1].sentiment == "BEARISH"
    assert "SPY" in posts[1].tickers_mentioned


def test_aggregate_subreddit():
    from app.social.reddit import RedditPost

    posts = [
        RedditPost("wsb", "Bull $AAPL rally", 100, 10, "", "", "BULLISH", ("AAPL",)),
        RedditPost("wsb", "Bear crash puts", 200, 20, "", "", "BEARISH", ()),
        RedditPost("wsb", "Neutral post", 50, 5, "", "", "NEUTRAL", ()),
    ]
    agg = _aggregate_subreddit("wsb", posts)
    assert agg.subreddit == "wsb"
    assert agg.bullish_count == 1
    assert agg.bearish_count == 1
    assert agg.neutral_count == 1
    assert agg.unusual_activity is False


@patch("app.social.reddit._get_reddit_token")
def test_fetch_reddit_summary_no_credentials(mock_token):
    mock_token.return_value = None
    result = fetch_reddit_summary()
    assert result is None


@patch("app.social.reddit.fetch_subreddit_posts")
@patch("app.social.reddit._get_reddit_token")
def test_fetch_reddit_summary_with_token(mock_token, mock_fetch):
    from app.social.reddit import RedditPost

    mock_token.return_value = "fake-token"
    mock_fetch.return_value = [
        RedditPost("wsb", "Bull rally", 100, 10, "", "", "BULLISH", ("AAPL",)),
    ]
    result = fetch_reddit_summary()
    assert result is not None
    assert len(result.subreddits) == 3
    assert result.overall_sentiment == "BULLISH"
