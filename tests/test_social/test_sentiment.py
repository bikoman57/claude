from __future__ import annotations

from app.social.sentiment import (
    classify_fed_tone,
    classify_sentiment,
    extract_tickers,
)


def test_classify_bullish():
    assert classify_sentiment("Markets rally, huge gains today!") == "BULLISH"


def test_classify_bearish():
    assert classify_sentiment("Stocks crash, panic selling!") == "BEARISH"


def test_classify_neutral():
    assert classify_sentiment("Company releases quarterly report") == "NEUTRAL"


def test_classify_mixed_bullish_wins():
    text = "Despite recession fears, market rally and surge continue"
    assert classify_sentiment(text) == "BULLISH"


def test_classify_fed_hawkish():
    assert classify_fed_tone("Inflation remains above target, tighten") == "HAWKISH"


def test_classify_fed_dovish():
    assert classify_fed_tone("Rate cut expected, easing ahead") == "DOVISH"


def test_classify_fed_neutral():
    assert classify_fed_tone("Meeting concluded, no changes") == "NEUTRAL"


def test_extract_tickers():
    tickers = extract_tickers("Buy $AAPL and $NVDA to the moon!")
    assert "AAPL" in tickers
    assert "NVDA" in tickers


def test_extract_tickers_empty():
    tickers = extract_tickers("No tickers here")
    assert tickers == []


def test_extract_tickers_ignores_long():
    tickers = extract_tickers("$TOOLONG should not match")
    assert tickers == []
