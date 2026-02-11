from __future__ import annotations

import re

HAWKISH_KEYWORDS: list[str] = [
    "inflation", "tighten", "restrictive", "rate increase",
    "strong labor", "above target", "vigilant", "price stability",
    "overheating", "persistent inflation",
]

DOVISH_KEYWORDS: list[str] = [
    "accommodation", "easing", "rate cut", "slowdown",
    "below target", "supportive", "patience", "downside risk",
    "soft landing", "gradual",
]

BULLISH_KEYWORDS: list[str] = [
    "rally", "surge", "moon", "bullish", "calls", "buy",
    "diamond hands", "to the moon", "rocket", "gains",
    "beat expectations", "upgrade", "outperform",
]

BEARISH_KEYWORDS: list[str] = [
    "crash", "puts", "bearish", "short", "sell",
    "recession", "collapse", "panic", "bag holder",
    "downgrade", "warning", "layoffs",
]

_TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


def classify_sentiment(text: str) -> str:
    """Classify text as BULLISH, BEARISH, or NEUTRAL."""
    lower = text.lower()
    bull = sum(1 for kw in BULLISH_KEYWORDS if kw in lower)
    bear = sum(1 for kw in BEARISH_KEYWORDS if kw in lower)
    if bull > bear:
        return "BULLISH"
    if bear > bull:
        return "BEARISH"
    return "NEUTRAL"


def classify_fed_tone(text: str) -> str:
    """Classify Fed-related text as HAWKISH, DOVISH, or NEUTRAL."""
    lower = text.lower()
    hawk = sum(1 for kw in HAWKISH_KEYWORDS if kw in lower)
    dove = sum(1 for kw in DOVISH_KEYWORDS if kw in lower)
    if hawk > dove:
        return "HAWKISH"
    if dove > hawk:
        return "DOVISH"
    return "NEUTRAL"


def extract_tickers(text: str) -> list[str]:
    """Extract $TICKER mentions from text."""
    return _TICKER_PATTERN.findall(text)
