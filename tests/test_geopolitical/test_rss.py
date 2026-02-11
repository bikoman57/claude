from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.geopolitical.rss import (
    GeopoliticalFeed,
    fetch_all_geopolitical_feeds,
    fetch_geopolitical_feed,
)

_SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>World News</title>
    <item>
      <title>Venezuela Crisis Deepens</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 10 Feb 2026 12:00:00 GMT</pubDate>
      <description>Political tensions escalate.</description>
    </item>
    <item>
      <title>Japan Defense Policy Shift</title>
      <link>https://example.com/2</link>
      <pubDate>Mon, 10 Feb 2026 11:00:00 GMT</pubDate>
      <description>Constitutional amendment proposed.</description>
    </item>
  </channel>
</rss>
"""

_FEED = GeopoliticalFeed("Test", "https://example.com/rss")


@patch("app.geopolitical.rss.httpx.Client")
def test_fetch_geopolitical_feed(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _SAMPLE_RSS
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_geopolitical_feed(_FEED)
    assert len(articles) == 2
    assert articles[0].title == "Venezuela Crisis Deepens"
    assert articles[0].source == "Test"


@patch("app.geopolitical.rss.httpx.Client")
def test_fetch_empty_feed(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = "<rss><channel><title>E</title></channel></rss>"
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_geopolitical_feed(_FEED)
    assert len(articles) == 0


@patch("app.geopolitical.rss.httpx.Client")
def test_fetch_all_skips_errors(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _SAMPLE_RSS
    mock_ctx = MagicMock()
    call_count = 0

    def side_effect(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("network")
        return mock_resp

    mock_ctx.get.side_effect = side_effect
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    feeds = [
        GeopoliticalFeed("Fail", "https://fail.com"),
        GeopoliticalFeed("OK", "https://ok.com"),
    ]
    articles = fetch_all_geopolitical_feeds(feeds)
    assert len(articles) == 2
