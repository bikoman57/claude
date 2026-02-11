from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.news.feeds import RSSFeed, fetch_all_feeds, fetch_feed

_SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Markets Rally on Fed News</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 10 Feb 2026 12:00:00 GMT</pubDate>
      <description>Stocks surge after rate cut announcement.</description>
      <dc:creator>Jane Reporter</dc:creator>
    </item>
    <item>
      <title>Oil Prices Plunge</title>
      <link>https://example.com/2</link>
      <pubDate>Mon, 10 Feb 2026 11:00:00 GMT</pubDate>
      <description>Crude falls on OPEC supply concerns.</description>
      <author>John Writer</author>
    </item>
  </channel>
</rss>
"""

_EMPTY_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel><title>Empty</title></channel>
</rss>
"""

_FEED = RSSFeed("Test", "https://example.com/rss", "general")


@patch("app.news.feeds.httpx.Client")
def test_fetch_feed_parses_articles(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _SAMPLE_RSS
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_feed(_FEED)
    assert len(articles) == 2
    assert articles[0].title == "Markets Rally on Fed News"
    assert articles[0].source == "Test"
    assert articles[0].author == "Jane Reporter"
    assert articles[1].author == "John Writer"


@patch("app.news.feeds.httpx.Client")
def test_fetch_feed_empty(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _EMPTY_RSS
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_feed(_FEED)
    assert len(articles) == 0


@patch("app.news.feeds.httpx.Client")
def test_fetch_feed_no_author(mock_client_cls):
    rss = """\
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>No Author Article</title>
      <link>https://example.com/3</link>
      <description>Test</description>
    </item>
  </channel>
</rss>
"""
    mock_resp = MagicMock()
    mock_resp.text = rss
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_feed(_FEED)
    assert len(articles) == 1
    assert articles[0].author is None


@patch("app.news.feeds.httpx.Client")
def test_fetch_all_feeds_skips_errors(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _SAMPLE_RSS
    mock_ctx = MagicMock()
    call_count = 0

    def side_effect(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("network error")
        return mock_resp

    mock_ctx.get.side_effect = side_effect
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    feeds = [
        RSSFeed("Fail", "https://fail.com/rss", "general"),
        RSSFeed("OK", "https://ok.com/rss", "general"),
    ]
    articles = fetch_all_feeds(feeds)
    assert len(articles) == 2


@patch("app.news.feeds.httpx.Client")
def test_fetch_feed_strips_whitespace(mock_client_cls):
    rss = """\
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>  Spaced Title  </title>
      <link>  https://example.com  </link>
      <description>  Desc  </description>
    </item>
  </channel>
</rss>
"""
    mock_resp = MagicMock()
    mock_resp.text = rss
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    articles = fetch_feed(_FEED)
    assert articles[0].title == "Spaced Title"
    assert articles[0].link == "https://example.com"
