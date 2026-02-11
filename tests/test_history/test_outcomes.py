from __future__ import annotations

import pytest

from app.history.outcomes import (
    get_completed_outcomes,
    load_outcomes,
    record_entry,
    record_exit,
)


def test_record_entry(tmp_path):
    path = tmp_path / "outcomes.json"
    outcome = record_entry(
        "TQQQ",
        "QQQ",
        45.00,
        factors={"vix_regime": "FAVORABLE"},
        path=path,
    )
    assert outcome.leveraged_ticker == "TQQQ"
    assert outcome.entry_price == 45.00
    assert outcome.exit_date is None
    assert outcome.factors_at_entry == {"vix_regime": "FAVORABLE"}

    loaded = load_outcomes(path)
    assert len(loaded) == 1
    assert loaded[0].leveraged_ticker == "TQQQ"


def test_record_exit(tmp_path):
    path = tmp_path / "outcomes.json"
    record_entry("TQQQ", "QQQ", 45.00, path=path)
    result = record_exit("TQQQ", 49.50, path=path)
    assert result is not None
    assert result.exit_price == 49.50
    assert result.pl_pct == pytest.approx(0.1)
    assert result.win is True


def test_record_exit_loss(tmp_path):
    path = tmp_path / "outcomes.json"
    record_entry("SOXL", "SOXX", 30.00, path=path)
    result = record_exit("SOXL", 27.00, path=path)
    assert result is not None
    assert result.pl_pct == pytest.approx(-0.1)
    assert result.win is False


def test_record_exit_not_found(tmp_path):
    path = tmp_path / "outcomes.json"
    result = record_exit("TQQQ", 49.50, path=path)
    assert result is None


def test_get_completed_outcomes(tmp_path):
    path = tmp_path / "outcomes.json"
    record_entry("TQQQ", "QQQ", 45.00, path=path)
    record_entry("SOXL", "SOXX", 30.00, path=path)
    record_exit("TQQQ", 49.50, path=path)

    completed = get_completed_outcomes(path)
    assert len(completed) == 1
    assert completed[0].leveraged_ticker == "TQQQ"


def test_load_empty(tmp_path):
    path = tmp_path / "outcomes.json"
    outcomes = load_outcomes(path)
    assert outcomes == []
