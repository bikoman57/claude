from __future__ import annotations

from pathlib import Path

from app.strategy.forecast import (
    ETFForecast,
    ForecastReport,
    compute_entry_probability,
    compute_expected_return,
    estimate_hold_days,
    generate_forecast,
    load_forecast,
    save_forecast,
)


def test_compute_entry_probability_signal():
    """SIGNAL state should give high base probability."""
    prob = compute_entry_probability("SIGNAL", {})
    assert 0.60 <= prob <= 0.80


def test_compute_entry_probability_watch():
    """WATCH state should give low base probability."""
    prob = compute_entry_probability("WATCH", {})
    assert 0.05 <= prob <= 0.25


def test_compute_entry_probability_favorable_factors():
    """Favorable factors should increase probability."""
    factors = {
        "drawdown_depth": "FAVORABLE",
        "vix_regime": "FAVORABLE",
        "fed_regime": "FAVORABLE",
    }
    prob_with = compute_entry_probability("ALERT", factors)
    prob_without = compute_entry_probability("ALERT", {})
    assert prob_with > prob_without


def test_compute_entry_probability_unfavorable_factors():
    """Unfavorable factors should decrease probability."""
    factors = {
        "drawdown_depth": "UNFAVORABLE",
        "vix_regime": "UNFAVORABLE",
        "fed_regime": "UNFAVORABLE",
    }
    prob_with = compute_entry_probability("SIGNAL", factors)
    prob_without = compute_entry_probability("SIGNAL", {})
    assert prob_with < prob_without


def test_compute_entry_probability_clamped():
    """Probability should be clamped to [0.05, 0.95]."""
    # All unfavorable on WATCH should clamp at 0.05
    factors = {f"factor_{i}": "UNFAVORABLE" for i in range(9)}
    prob = compute_entry_probability("WATCH", factors)
    assert prob >= 0.05

    # All favorable on TARGET should clamp at 0.95
    factors = {f"factor_{i}": "FAVORABLE" for i in range(9)}
    prob = compute_entry_probability("TARGET", factors)
    assert prob <= 0.95


def test_compute_entry_probability_with_backtest():
    """Blending with backtest win rate should work."""
    prob_no_bt = compute_entry_probability("SIGNAL", {})
    prob_high_bt = compute_entry_probability("SIGNAL", {}, backtest_win_rate=0.90)
    prob_low_bt = compute_entry_probability("SIGNAL", {}, backtest_win_rate=0.10)

    assert prob_high_bt > prob_no_bt
    assert prob_low_bt < prob_no_bt


def test_compute_expected_return_positive():
    """High probability with positive avg gain should give positive return."""
    ret = compute_expected_return(
        entry_probability=0.70,
        avg_gain=0.10,
        avg_loss=-0.15,
    )
    # 0.70 * 0.10 + 0.30 * (-0.15) = 0.07 - 0.045 = 0.025
    assert ret > 0


def test_compute_expected_return_negative():
    """Low probability should give negative expected return."""
    ret = compute_expected_return(
        entry_probability=0.20,
        avg_gain=0.10,
        avg_loss=-0.15,
    )
    # 0.20 * 0.10 + 0.80 * (-0.15) = 0.02 - 0.12 = -0.10
    assert ret < 0


def test_compute_expected_return_defaults():
    """Should use profit_target/stop_loss as defaults."""
    ret = compute_expected_return(
        entry_probability=0.50,
        avg_gain=None,
        avg_loss=None,
        profit_target=0.10,
        stop_loss=0.15,
    )
    # 0.50 * 0.10 + 0.50 * (-0.15) = 0.05 - 0.075 = -0.025
    assert -0.03 < ret < -0.02


def test_estimate_hold_days_with_duration():
    """Should use average trade duration when available."""
    days = estimate_hold_days(avg_trade_duration=12.5)
    assert days in (12, 13)  # Python rounds 12.5 to 12 (banker's rounding)


def test_estimate_hold_days_defaults():
    """Should use signal-state defaults when no duration available."""
    assert estimate_hold_days(signal_state="SIGNAL") == 10
    assert estimate_hold_days(signal_state="WATCH") == 20


def test_generate_forecast_basic():
    """Should generate forecasts from signal data."""
    signals = [
        {
            "leveraged_ticker": "TQQQ",
            "underlying_ticker": "QQQ",
            "state": "SIGNAL",
            "underlying_drawdown_pct": -0.06,
        },
        {
            "leveraged_ticker": "UPRO",
            "underlying_ticker": "SPY",
            "state": "WATCH",
            "underlying_drawdown_pct": -0.02,
        },
    ]
    report = generate_forecast(signals)
    assert len(report.forecasts) == 2
    assert report.date
    # SIGNAL state should have higher probability
    tqqq = next(f for f in report.forecasts if f.leveraged_ticker == "TQQQ")
    upro = next(f for f in report.forecasts if f.leveraged_ticker == "UPRO")
    assert tqqq.entry_probability > upro.entry_probability


def test_generate_forecast_with_backtests():
    """Backtest data should be incorporated."""
    signals = [
        {
            "leveraged_ticker": "TQQQ",
            "underlying_ticker": "QQQ",
            "state": "ALERT",
            "underlying_drawdown_pct": -0.04,
        },
    ]
    backtests = [
        {
            "leveraged_ticker": "TQQQ",
            "underlying_ticker": "QQQ",
            "strategy_type": "rsi_oversold",
            "sharpe_ratio": 1.5,
            "win_rate": 0.65,
            "avg_gain": 0.12,
            "avg_loss": -0.08,
            "profit_target": 0.10,
            "trades": [
                {"entry_day": 0, "exit_day": 10},
                {"entry_day": 20, "exit_day": 35},
            ],
        },
    ]
    report = generate_forecast(signals, backtests)
    assert len(report.forecasts) == 1
    fc = report.forecasts[0]
    assert fc.best_strategy == "rsi_oversold"


def test_generate_forecast_empty():
    """Empty signals should produce empty report."""
    report = generate_forecast([])
    assert len(report.forecasts) == 0
    assert report.actionable_count == 0


def test_save_load_roundtrip(tmp_path: Path):
    """Save and load should preserve data."""
    report = ForecastReport(
        date="2026-02-12",
        forecasts=(
            ETFForecast(
                leveraged_ticker="TQQQ",
                underlying_ticker="QQQ",
                signal_state="SIGNAL",
                current_drawdown_pct=-0.06,
                confidence_level="MEDIUM",
                entry_probability=0.65,
                expected_return_pct=0.025,
                expected_hold_days=12,
                best_strategy="ath_mean_reversion",
                factor_scores={"drawdown_depth": "FAVORABLE"},
            ),
        ),
        actionable_count=1,
    )
    path = tmp_path / "test_forecast.json"
    save_forecast(report, path)
    loaded = load_forecast(path)

    assert loaded.date == report.date
    assert len(loaded.forecasts) == 1
    assert loaded.forecasts[0].leveraged_ticker == "TQQQ"
    assert loaded.forecasts[0].entry_probability == 0.65
    assert loaded.actionable_count == 1
