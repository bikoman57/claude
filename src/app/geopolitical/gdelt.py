from __future__ import annotations

from dataclasses import dataclass

import httpx

_GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass(frozen=True, slots=True)
class GdeltQuery:
    """A GDELT API query configuration."""

    theme: str
    timespan: str
    max_results: int


@dataclass(frozen=True, slots=True)
class GdeltEvent:
    """An event from the GDELT API."""

    title: str
    url: str
    source: str
    tone: float
    volume: int
    theme: str
    date: str


TRACKED_THEMES: list[GdeltQuery] = [
    GdeltQuery("TRADE_WAR", "7d", 50),
    GdeltQuery("MILITARY", "7d", 50),
    GdeltQuery("SANCTIONS", "7d", 50),
    GdeltQuery("ECON_TARIFF", "7d", 50),
    GdeltQuery("ELECTION", "7d", 30),
    GdeltQuery("TERRITORY", "7d", 30),
]


def fetch_gdelt_events(query: GdeltQuery) -> list[GdeltEvent]:
    """Fetch events from the GDELT API for a given theme."""
    params = {
        "query": f"theme:{query.theme}",
        "format": "json",
        "timespan": query.timespan,
        "maxrecords": str(query.max_results),
        "sort": "DateDesc",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(_GDELT_DOC_API, params=params, follow_redirects=True)
        resp.raise_for_status()

    data = resp.json()
    articles = data.get("articles", [])

    events: list[GdeltEvent] = []
    for article in articles:
        title = article.get("title", "")
        if not title:
            continue
        events.append(
            GdeltEvent(
                title=title,
                url=article.get("url", ""),
                source=article.get("domain", ""),
                tone=float(article.get("tone", 0.0)),
                volume=int(article.get("socialimage", 0) or 0),
                theme=query.theme,
                date=article.get("seendate", ""),
            ),
        )
    return events


def fetch_all_gdelt_events(
    queries: list[GdeltQuery] | None = None,
) -> list[GdeltEvent]:
    """Fetch events for all tracked themes, skipping errors."""
    import contextlib

    target = queries if queries is not None else TRACKED_THEMES
    all_events: list[GdeltEvent] = []
    for query in target:
        with contextlib.suppress(Exception):
            all_events.extend(fetch_gdelt_events(query))
    return all_events
