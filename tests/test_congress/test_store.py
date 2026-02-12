from __future__ import annotations

import json
from datetime import UTC, datetime

from app.congress.fetcher import Chamber, CongressTrade, TransactionType
from app.congress.store import (
    is_cache_stale,
    load_fetch_meta,
    load_member_ratings,
    load_trades,
    save_fetch_meta,
    save_member_ratings,
    save_trades,
)


def _make_trade() -> CongressTrade:
    return CongressTrade(
        member_name="Test Member",
        chamber=Chamber.HOUSE,
        party="D",
        state="CA",
        ticker="AAPL",
        asset_description="Apple Inc.",
        transaction_type=TransactionType.PURCHASE,
        trade_date="2025-01-15",
        filing_date="2025-02-01",
        amount_low=1001.0,
        amount_high=15000.0,
        owner="Self",
        source="house",
    )


def test_load_empty(tmp_path):
    result = load_trades(tmp_path / "nonexistent.json")
    assert result == []


def test_save_load_trades_roundtrip(tmp_path):
    path = tmp_path / "trades.json"
    trades = [_make_trade()]
    save_trades(trades, path)
    loaded = load_trades(path)
    assert len(loaded) == 1
    assert loaded[0].member_name == "Test Member"
    assert loaded[0].ticker == "AAPL"
    assert loaded[0].chamber == Chamber.HOUSE


def test_member_ratings_roundtrip(tmp_path):
    path = tmp_path / "ratings.json"
    ratings = [{"name": "Test", "tier": "A", "win_rate": 0.75}]
    save_member_ratings(ratings, path)
    loaded = load_member_ratings(path)
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Test"


def test_fetch_meta_roundtrip(tmp_path):
    path = tmp_path / "meta.json"
    meta = {"house_last_fetch": datetime.now(tz=UTC).isoformat()}
    save_fetch_meta(meta, path)
    loaded = load_fetch_meta(path)
    assert "house_last_fetch" in loaded


def test_cache_stale_no_meta(tmp_path):
    assert is_cache_stale("house", path=tmp_path / "nonexistent.json")


def test_cache_fresh(tmp_path):
    path = tmp_path / "meta.json"
    meta = {"house_last_fetch": datetime.now(tz=UTC).isoformat()}
    path.write_text(json.dumps(meta))
    assert not is_cache_stale("house", ttl_hours=6, path=path)


def test_cache_stale_old(tmp_path):
    path = tmp_path / "meta.json"
    # Set to 10 hours ago
    from datetime import timedelta

    old_time = (datetime.now(tz=UTC) - timedelta(hours=10)).isoformat()
    meta = {"house_last_fetch": old_time}
    path.write_text(json.dumps(meta))
    assert is_cache_stale("house", ttl_hours=6, path=path)
