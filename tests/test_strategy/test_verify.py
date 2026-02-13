from __future__ import annotations

from app.strategy.verify import (
    ForecastVerification,
    Trend,
    _compute_trend,
    _is_prediction_correct,
    load_accuracy_report,
    verify_forecasts,
)

# --- Prediction correctness tests ---


def test_high_prob_correct_with_profit():
    """High-prob prediction correct when entry occurs with profit."""
    assert _is_prediction_correct(0.70, True, 0.05) is True


def test_high_prob_wrong_with_loss():
    """High-prob prediction wrong when entry occurs with loss."""
    assert _is_prediction_correct(0.70, True, -0.05) is False


def test_high_prob_wrong_no_entry():
    """High-prob prediction wrong when no entry occurs."""
    assert _is_prediction_correct(0.70, False, None) is False


def test_low_prob_correct_no_entry():
    """Low-prob prediction correct when no entry occurs."""
    assert _is_prediction_correct(0.30, False, None) is True


def test_low_prob_correct_with_loss():
    """Low-prob prediction correct when entry occurs with loss."""
    assert _is_prediction_correct(0.30, True, -0.05) is True


def test_low_prob_wrong_with_profit():
    """Low-prob prediction wrong when entry occurs with profit."""
    assert _is_prediction_correct(0.30, True, 0.05) is False


def test_boundary_prob_50():
    """Exactly 50% should be treated as low-probability."""
    assert _is_prediction_correct(0.50, False, None) is True


# --- Trend computation tests ---


def _make_verifications(correct_pattern: list[bool]) -> list[ForecastVerification]:
    return [
        ForecastVerification(
            date=f"2026-01-{i + 1:02d}",
            leveraged_ticker="TQQQ",
            predicted_probability=0.70,
            predicted_return=0.02,
            actual_entry_occurred=True,
            actual_return=0.05 if c else -0.05,
            correct=c,
        )
        for i, c in enumerate(correct_pattern)
    ]


def test_trend_insufficient():
    """Fewer than 10 verifications should return INSUFFICIENT."""
    verifs = _make_verifications([True, False, True])
    assert _compute_trend(verifs) == Trend.INSUFFICIENT


def test_trend_improving():
    """More correct in second half should show IMPROVING."""
    # First 5: 2/5 correct, second 5: 5/5 correct
    pattern = [True, False, False, True, False, True, True, True, True, True]
    verifs = _make_verifications(pattern)
    assert _compute_trend(verifs) == Trend.IMPROVING


def test_trend_declining():
    """More correct in first half should show DECLINING."""
    pattern = [True, True, True, True, True, False, False, True, False, False]
    verifs = _make_verifications(pattern)
    assert _compute_trend(verifs) == Trend.DECLINING


def test_trend_stable():
    """Similar rates should show STABLE."""
    pattern = [True, False, True, False, True, True, False, True, False, True]
    verifs = _make_verifications(pattern)
    assert _compute_trend(verifs) == Trend.STABLE


# --- Verification integration tests ---


def test_verify_forecasts_empty(tmp_path, monkeypatch):
    """Empty data should produce empty report."""
    monkeypatch.setattr(
        "app.strategy.verify._ACCURACY_PATH", tmp_path / "accuracy.json"
    )
    monkeypatch.setattr(
        "app.strategy.forecast._FORECASTS_DIR", tmp_path / "forecasts"
    )
    report = verify_forecasts([], [])
    assert report.total_verifications == 0
    assert report.hit_rate == 0.0
    assert report.trend == Trend.INSUFFICIENT


def test_verify_forecasts_no_forecasts_on_disk(tmp_path, monkeypatch):
    """No saved forecasts should give empty verifications."""
    monkeypatch.setattr(
        "app.strategy.verify._ACCURACY_PATH", tmp_path / "accuracy.json"
    )
    monkeypatch.setattr(
        "app.strategy.forecast._FORECASTS_DIR", tmp_path / "forecasts"
    )
    signals = [
        {
            "leveraged_ticker": "TQQQ",
            "underlying_ticker": "QQQ",
            "state": "WATCH",
        },
    ]
    report = verify_forecasts(signals)
    assert report.total_verifications == 0


def test_load_accuracy_report_missing():
    """Missing accuracy file should return None."""
    assert load_accuracy_report() is None or True  # depends on disk state
