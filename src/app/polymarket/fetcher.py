"""Polymarket prediction markets: fetch and filter relevant markets."""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

_GAMMA_API = "https://gamma-api.polymarket.com"
_TIMEOUT = 15.0
_CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "polymarket"
)
_DEFAULT_TTL_HOURS = 2
_MAX_EVENTS = 300
_MIN_VOLUME = 10_000
_MIN_LIQUIDITY = 5_000


@dataclass(frozen=True, slots=True)
class PolymarketMarket:
    """A single prediction market from Polymarket."""

    market_id: str
    question: str
    slug: str
    outcomes: tuple[str, ...]
    outcome_prices: tuple[float, ...]
    volume: float
    liquidity: float
    end_date: str
    active: bool
    event_slug: str
    event_title: str
    tags: tuple[str, ...]


def _match_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    """Check if any keyword appears in text (case-insensitive)."""
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _parse_market(
    market: dict[str, Any],
    event: dict[str, Any],
) -> PolymarketMarket | None:
    """Parse a market dict from the Gamma API into a PolymarketMarket."""
    market_id = str(market.get("id", ""))
    question = str(market.get("question", ""))
    if not market_id or not question:
        return None

    slug = str(market.get("slug", ""))
    active = bool(market.get("active", False))
    end_date = str(market.get("endDate", ""))

    # Parse outcomes and prices
    outcomes_raw = market.get("outcomes", "")
    if isinstance(outcomes_raw, str):
        with contextlib.suppress(json.JSONDecodeError):
            outcomes_raw = json.loads(outcomes_raw)
    outcomes = (
        tuple(str(o) for o in outcomes_raw)
        if isinstance(outcomes_raw, list)
        else ()
    )

    prices_raw = market.get("outcomePrices", "")
    if isinstance(prices_raw, str):
        with contextlib.suppress(json.JSONDecodeError):
            prices_raw = json.loads(prices_raw)
    outcome_prices = tuple(
        float(p) for p in prices_raw
    ) if isinstance(prices_raw, list) else ()

    volume = float(market.get("volume", 0) or 0)
    liquidity = float(market.get("liquidity", 0) or 0)

    event_slug = str(event.get("slug", ""))
    event_title = str(event.get("title", ""))

    tags_raw = event.get("tags", [])
    tags = tuple(
        str(t.get("label", "") if isinstance(t, dict) else t)
        for t in tags_raw
    ) if isinstance(tags_raw, list) else ()

    return PolymarketMarket(
        market_id=market_id,
        question=question,
        slug=slug,
        outcomes=outcomes,
        outcome_prices=outcome_prices,
        volume=volume,
        liquidity=liquidity,
        end_date=end_date,
        active=active,
        event_slug=event_slug,
        event_title=event_title,
        tags=tags,
    )


def fetch_active_events(max_events: int = _MAX_EVENTS) -> list[PolymarketMarket]:
    """Fetch active events from Polymarket sorted by 24h volume."""
    all_markets: list[PolymarketMarket] = []
    page_size = 100
    offset = 0

    with httpx.Client(timeout=_TIMEOUT) as client:
        while offset < max_events:
            params = {
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": str(page_size),
                "offset": str(offset),
            }
            try:
                resp = client.get(
                    f"{_GAMMA_API}/events",
                    params=params,
                    follow_redirects=True,
                )
                resp.raise_for_status()
            except httpx.HTTPError:
                break

            events = resp.json()
            if not isinstance(events, list) or not events:
                break

            for event in events:
                if not isinstance(event, dict):
                    continue
                markets_raw = event.get("markets", [])
                if not isinstance(markets_raw, list):
                    continue
                for mkt in markets_raw:
                    if not isinstance(mkt, dict):
                        continue
                    parsed = _parse_market(mkt, event)
                    if parsed is not None:
                        all_markets.append(parsed)

            offset += page_size

    return all_markets


def fetch_relevant_markets(
    *,
    force_refresh: bool = False,
) -> list[PolymarketMarket]:
    """Fetch markets relevant to our trading system.

    Fetches active events, filters by keyword match against tracked
    queries, applies volume/liquidity thresholds, deduplicates.
    """
    from app.polymarket.classifier import TRACKED_QUERIES

    # Check cache
    if not force_refresh and not _is_cache_stale():
        cached = _load_cached()
        if cached is not None:
            return cached

    all_markets = fetch_active_events()
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    seen: set[str] = set()
    relevant: list[PolymarketMarket] = []

    for market in all_markets:
        # Skip duplicates
        if market.market_id in seen:
            continue

        # Skip inactive or expired
        if not market.active:
            continue
        if market.end_date and market.end_date < today:
            continue

        # Skip low volume/liquidity
        if market.volume < _MIN_VOLUME or market.liquidity < _MIN_LIQUIDITY:
            continue

        # Check keyword match
        text = f"{market.question} {market.event_title}"
        matched = any(
            _match_keywords(text, q.keywords) for q in TRACKED_QUERIES
        )
        if not matched:
            continue

        seen.add(market.market_id)
        relevant.append(market)

    # Cache results
    _save_cache(relevant)
    _update_fetch_meta()

    return relevant


# --- Caching ---


def _is_cache_stale(ttl_hours: int = _DEFAULT_TTL_HOURS) -> bool:
    """Check if cache is stale based on TTL."""
    meta_path = _CACHE_DIR / "fetch_meta.json"
    if not meta_path.exists():
        return True
    with contextlib.suppress(Exception):
        meta = json.loads(meta_path.read_text())
        last_fetch = meta.get("last_fetch")
        if last_fetch:
            fetched_at = datetime.fromisoformat(last_fetch)
            return datetime.now(tz=UTC) - fetched_at > timedelta(hours=ttl_hours)
    return True


def _load_cached() -> list[PolymarketMarket] | None:
    """Load cached markets from disk."""
    cache_path = _CACHE_DIR / "markets_raw.json"
    if not cache_path.exists():
        return None
    with contextlib.suppress(Exception):
        data = json.loads(cache_path.read_text())
        if isinstance(data, list):
            markets: list[PolymarketMarket] = []
            for raw in data:
                if isinstance(raw, dict):
                    with contextlib.suppress(Exception):
                        markets.append(PolymarketMarket(
                            market_id=str(raw["market_id"]),
                            question=str(raw["question"]),
                            slug=str(raw.get("slug", "")),
                            outcomes=tuple(raw.get("outcomes", ())),
                            outcome_prices=tuple(
                            float(p)
                            for p in raw.get("outcome_prices", ())
                        ),
                            volume=float(raw.get("volume", 0)),
                            liquidity=float(raw.get("liquidity", 0)),
                            end_date=str(raw.get("end_date", "")),
                            active=bool(raw.get("active", True)),
                            event_slug=str(raw.get("event_slug", "")),
                            event_title=str(raw.get("event_title", "")),
                            tags=tuple(raw.get("tags", ())),
                        ))
            return markets
    return None


def _save_cache(markets: list[PolymarketMarket]) -> None:
    """Save markets to cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CACHE_DIR / "markets_raw.json"
    data = [
        {
            "market_id": m.market_id,
            "question": m.question,
            "slug": m.slug,
            "outcomes": list(m.outcomes),
            "outcome_prices": list(m.outcome_prices),
            "volume": m.volume,
            "liquidity": m.liquidity,
            "end_date": m.end_date,
            "active": m.active,
            "event_slug": m.event_slug,
            "event_title": m.event_title,
            "tags": list(m.tags),
        }
        for m in markets
    ]
    cache_path.write_text(json.dumps(data, indent=2))


def _update_fetch_meta() -> None:
    """Update fetch metadata with current timestamp."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = _CACHE_DIR / "fetch_meta.json"
    meta: dict[str, object] = {}
    if meta_path.exists():
        with contextlib.suppress(Exception):
            meta = json.loads(meta_path.read_text())
    meta["last_fetch"] = datetime.now(tz=UTC).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2))
