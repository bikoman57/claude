from __future__ import annotations

from app.etf.universe import (
    ETF_UNIVERSE,
    get_all_underlying_tickers,
    get_mapping,
    get_mapping_by_underlying,
)


def test_universe_not_empty():
    assert len(ETF_UNIVERSE) > 0


def test_get_mapping_found():
    m = get_mapping("TQQQ")
    assert m is not None
    assert m.underlying_ticker == "QQQ"
    assert m.leverage == 3.0


def test_get_mapping_case_insensitive():
    m = get_mapping("tqqq")
    assert m is not None
    assert m.leveraged_ticker == "TQQQ"


def test_get_mapping_not_found():
    assert get_mapping("FAKE") is None


def test_get_mapping_by_underlying():
    m = get_mapping_by_underlying("QQQ")
    assert m is not None
    assert m.leveraged_ticker == "TQQQ"


def test_get_mapping_by_underlying_not_found():
    assert get_mapping_by_underlying("FAKE") is None


def test_get_all_underlying_tickers_no_duplicates():
    tickers = get_all_underlying_tickers()
    assert len(tickers) == len(set(tickers))


def test_all_mappings_have_valid_thresholds():
    for m in ETF_UNIVERSE:
        assert 0 < m.alert_threshold < m.drawdown_threshold
        assert 0 < m.profit_target <= 1.0
        assert m.leverage >= 1.0
