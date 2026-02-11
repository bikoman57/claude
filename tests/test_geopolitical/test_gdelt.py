from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.geopolitical.gdelt import (
    GdeltQuery,
    fetch_all_gdelt_events,
    fetch_gdelt_events,
)

_SAMPLE_RESPONSE = {
    "articles": [
        {
            "title": "US-China Trade Tensions Rise",
            "url": "https://example.com/1",
            "domain": "reuters.com",
            "tone": -3.5,
            "socialimage": 120,
            "seendate": "20260210T120000Z",
        },
        {
            "title": "Tariff Talks Continue",
            "url": "https://example.com/2",
            "domain": "bbc.co.uk",
            "tone": -1.2,
            "socialimage": 30,
            "seendate": "20260210T100000Z",
        },
        {
            "title": "",
            "url": "https://example.com/3",
            "domain": "empty.com",
            "tone": 0.0,
            "socialimage": 0,
            "seendate": "",
        },
    ],
}

_QUERY = GdeltQuery("TRADE_WAR", "7d", 50)


@patch("app.geopolitical.gdelt.httpx.Client")
def test_fetch_gdelt_events(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    events = fetch_gdelt_events(_QUERY)
    assert len(events) == 2  # Empty title skipped
    assert events[0].title == "US-China Trade Tensions Rise"
    assert events[0].tone == -3.5
    assert events[0].theme == "TRADE_WAR"


@patch("app.geopolitical.gdelt.httpx.Client")
def test_fetch_gdelt_empty_response(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"articles": []}
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    events = fetch_gdelt_events(_QUERY)
    assert len(events) == 0


@patch("app.geopolitical.gdelt.httpx.Client")
def test_fetch_gdelt_no_articles_key(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    events = fetch_gdelt_events(_QUERY)
    assert len(events) == 0


@patch("app.geopolitical.gdelt.httpx.Client")
def test_fetch_all_skips_errors(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_ctx = MagicMock()
    call_count = 0

    def side_effect(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API error")
        return mock_resp

    mock_ctx.get.side_effect = side_effect
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    queries = [
        GdeltQuery("FAIL", "7d", 10),
        GdeltQuery("TRADE_WAR", "7d", 10),
    ]
    events = fetch_all_gdelt_events(queries)
    assert len(events) == 2
