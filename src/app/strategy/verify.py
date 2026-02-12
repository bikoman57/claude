"""Forecast verification — tracks accuracy of entry probability predictions.

Compares past forecasts against actual signal outcomes (did a trade entry
actually occur?) and tracks hit rate over time.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from app.strategy.forecast import list_forecasts, load_forecast

_ACCURACY_PATH = Path("data/forecast_accuracy.json")


class Trend(StrEnum):
    """Accuracy trend direction."""

    IMPROVING = "IMPROVING"
    DECLINING = "DECLINING"
    STABLE = "STABLE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ForecastVerification:
    """Verification of one ETF forecast."""

    date: str
    leveraged_ticker: str
    predicted_probability: float
    predicted_return: float
    actual_entry_occurred: bool
    actual_return: float | None  # None if no entry
    correct: bool


@dataclass(frozen=True, slots=True)
class AccuracyReport:
    """Accuracy tracking across all forecasts."""

    total_verifications: int
    correct_count: int
    hit_rate: float  # correct / total
    recent_hit_rate: float | None  # last 10 verifications
    trend: str  # IMPROVING, DECLINING, STABLE, INSUFFICIENT
    verifications: tuple[ForecastVerification, ...]


def _is_prediction_correct(
    predicted_probability: float,
    actual_entry_occurred: bool,
    actual_return: float | None,
) -> bool:
    """Determine if a forecast was correct.

    High-probability (>0.5) forecast is correct if:
      - Entry occurred AND return was positive
    Low-probability (<=0.5) forecast is correct if:
      - No entry occurred OR entry resulted in a loss
    """
    high_prob = predicted_probability > 0.50

    if high_prob:
        # Correct if entry happened with profit
        if actual_entry_occurred and actual_return is not None:
            return actual_return > 0
        return False
    # Low-prob correct if no entry, or entry was a loss
    if not actual_entry_occurred:
        return True
    if actual_return is not None:
        return actual_return <= 0
    return True


def _compute_trend(verifications: list[ForecastVerification]) -> str:
    """Compute accuracy trend from verification history.

    Compares first-half vs second-half hit rates.
    Needs 10+ verifications for a meaningful trend.
    """
    if len(verifications) < 10:
        return Trend.INSUFFICIENT

    mid = len(verifications) // 2
    first_half = verifications[:mid]
    second_half = verifications[mid:]

    first_rate = sum(1 for v in first_half if v.correct) / len(first_half)
    second_rate = sum(1 for v in second_half if v.correct) / len(second_half)

    diff = second_rate - first_rate
    if diff > 0.05:
        return Trend.IMPROVING
    if diff < -0.05:
        return Trend.DECLINING
    return Trend.STABLE


def verify_forecasts(
    signals_data: list[dict[str, object]],
    backtest_data: list[dict[str, object]] | None = None,
) -> AccuracyReport:
    """Verify past forecasts against current signal/trade data.

    Loads all saved forecasts, checks each ETF prediction against
    whether a trade entry actually occurred and its return.
    """
    # Build lookup of current signal states and active trades
    signal_lookup: dict[str, dict[str, object]] = {}
    for sig in signals_data:
        if isinstance(sig, dict):
            ticker = str(sig.get("leveraged_ticker", ""))
            if ticker:
                signal_lookup[ticker] = sig

    # Build backtest lookup for actual returns
    bt_lookup: dict[str, dict[str, object]] = {}
    if backtest_data:
        for bt in backtest_data:
            if isinstance(bt, dict):
                ticker = str(bt.get("leveraged_ticker", ""))
                if ticker:
                    existing = bt_lookup.get(ticker)
                    sharpe = bt.get("sharpe_ratio")
                    if existing is None:
                        bt_lookup[ticker] = bt
                    elif isinstance(sharpe, (int, float)):
                        ex_sharpe = existing.get("sharpe_ratio")
                        if (
                            not isinstance(ex_sharpe, (int, float))
                            or sharpe > ex_sharpe
                        ):
                            bt_lookup[ticker] = bt

    # Load existing accuracy data
    existing_verifications = _load_verifications()
    seen_keys: set[str] = {
        f"{v.date}:{v.leveraged_ticker}" for v in existing_verifications
    }

    # Process saved forecasts
    new_verifications: list[ForecastVerification] = list(existing_verifications)
    forecast_files = list_forecasts()

    for fpath in forecast_files:
        try:
            report = load_forecast(fpath)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

        for fc in report.forecasts:
            key = f"{report.date}:{fc.leveraged_ticker}"
            if key in seen_keys:
                continue

            # Determine if entry actually occurred
            sig = signal_lookup.get(fc.leveraged_ticker, {})
            state = str(sig.get("state", "WATCH"))
            actual_entry = state in ("ACTIVE", "TARGET", "SIGNAL")

            # Get actual return from backtest (most recent trades)
            actual_return: float | None = None
            bt = bt_lookup.get(fc.leveraged_ticker, {})
            trades = bt.get("trades", [])
            if isinstance(trades, list) and trades:
                last_trade = trades[-1]
                if isinstance(last_trade, dict):
                    ret = last_trade.get("leveraged_return")
                    if isinstance(ret, (int, float)):
                        actual_return = ret

            correct = _is_prediction_correct(
                fc.entry_probability,
                actual_entry,
                actual_return,
            )

            verification = ForecastVerification(
                date=report.date,
                leveraged_ticker=fc.leveraged_ticker,
                predicted_probability=fc.entry_probability,
                predicted_return=fc.expected_return_pct,
                actual_entry_occurred=actual_entry,
                actual_return=actual_return,
                correct=correct,
            )
            new_verifications.append(verification)
            seen_keys.add(key)

    # Sort chronologically
    new_verifications.sort(key=lambda v: (v.date, v.leveraged_ticker))

    total = len(new_verifications)
    correct_count = sum(1 for v in new_verifications if v.correct)
    hit_rate = correct_count / total if total > 0 else 0.0

    # Recent hit rate (last 10)
    recent_hit_rate: float | None = None
    if len(new_verifications) >= 10:
        recent = new_verifications[-10:]
        recent_hit_rate = sum(1 for v in recent if v.correct) / 10.0

    trend = _compute_trend(new_verifications)

    accuracy = AccuracyReport(
        total_verifications=total,
        correct_count=correct_count,
        hit_rate=round(hit_rate, 4),
        recent_hit_rate=(
            round(recent_hit_rate, 4) if recent_hit_rate is not None else None
        ),
        trend=trend,
        verifications=tuple(new_verifications),
    )

    _save_verifications(accuracy)
    return accuracy


def _load_verifications() -> list[ForecastVerification]:
    """Load existing verifications from disk."""
    if not _ACCURACY_PATH.exists():
        return []
    try:
        data = json.loads(_ACCURACY_PATH.read_text(encoding="utf-8"))
        return [ForecastVerification(**v) for v in data.get("verifications", [])]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _save_verifications(report: AccuracyReport) -> Path:
    """Save accuracy report to disk."""
    _ACCURACY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ACCURACY_PATH.write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )
    return _ACCURACY_PATH


def load_accuracy_report() -> AccuracyReport | None:
    """Load the latest accuracy report."""
    if not _ACCURACY_PATH.exists():
        return None
    try:
        data = json.loads(_ACCURACY_PATH.read_text(encoding="utf-8"))
        verifications = tuple(
            ForecastVerification(**v) for v in data.get("verifications", [])
        )
        return AccuracyReport(
            total_verifications=data.get("total_verifications", 0),
            correct_count=data.get("correct_count", 0),
            hit_rate=data.get("hit_rate", 0.0),
            recent_hit_rate=data.get("recent_hit_rate"),
            trend=data.get("trend", Trend.INSUFFICIENT),
            verifications=verifications,
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
