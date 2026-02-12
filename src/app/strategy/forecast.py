"""Forecast generation for leveraged ETF swing trades.

Produces per-ETF entry probability estimates based on signal state,
confidence factors, and backtest win rates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.etf.confidence import ConfidenceLevel, FactorAssessment
from app.etf.signals import SignalState

_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
_FORECASTS_DIR = Path("data/forecasts")

# Base entry probabilities by signal state
_BASE_PROBABILITY: dict[str, float] = {
    SignalState.SIGNAL: 0.70,
    SignalState.ALERT: 0.40,
    SignalState.WATCH: 0.15,
    SignalState.ACTIVE: 0.85,
    SignalState.TARGET: 0.95,
}

# Default factor weights (used when no learned weights available)
_DEFAULT_WEIGHTS: dict[str, float] = {
    "drawdown_depth": 0.20,
    "vix_regime": 0.15,
    "fed_regime": 0.10,
    "yield_curve": 0.08,
    "earnings_risk": 0.07,
    "geopolitical_risk": 0.10,
    "social_sentiment": 0.08,
    "news_sentiment": 0.10,
    "market_statistics": 0.12,
}


@dataclass(frozen=True, slots=True)
class ETFForecast:
    """Forecast for a single ETF."""

    leveraged_ticker: str
    underlying_ticker: str
    signal_state: str
    current_drawdown_pct: float
    confidence_level: str
    entry_probability: float  # 0.0 to 1.0
    expected_return_pct: float
    expected_hold_days: int
    best_strategy: str
    factor_scores: dict[str, str]  # factor_name -> assessment


@dataclass(frozen=True, slots=True)
class ForecastReport:
    """Full forecast report for a date."""

    date: str
    forecasts: tuple[ETFForecast, ...]
    actionable_count: int  # forecasts with entry_probability > 0.50


def compute_entry_probability(
    signal_state: str,
    factor_assessments: dict[str, str],
    backtest_win_rate: float | None = None,
    factor_weights: dict[str, float] | None = None,
) -> float:
    """Compute entry probability from signal state, factors, and backtest data.

    Algorithm:
    1. Start with base probability from signal state
    2. Adjust by weighted factor assessments (FAVORABLE +weight*0.15,
       UNFAVORABLE -weight*0.15)
    3. Blend 60/40 with backtest win rate if available
    4. Clamp to [0.05, 0.95]
    """
    base = _BASE_PROBABILITY.get(signal_state, 0.15)
    weights = factor_weights or _DEFAULT_WEIGHTS

    adjustment = 0.0
    for factor_name, assessment in factor_assessments.items():
        w = weights.get(factor_name, 0.1)
        if assessment == FactorAssessment.FAVORABLE:
            adjustment += w * 0.15
        elif assessment == FactorAssessment.UNFAVORABLE:
            adjustment -= w * 0.15

    adjusted = base + adjustment

    # Blend with backtest win rate if available
    if backtest_win_rate is not None and backtest_win_rate > 0:
        adjusted = 0.60 * adjusted + 0.40 * backtest_win_rate

    return max(0.05, min(0.95, adjusted))


def compute_expected_return(
    entry_probability: float,
    avg_gain: float | None,
    avg_loss: float | None,
    profit_target: float = 0.10,
    stop_loss: float = 0.15,
) -> float:
    """Compute expected return from probability and avg gain/loss.

    Uses backtest averages if available, otherwise falls back to
    profit_target and stop_loss as estimates.
    """
    gain = avg_gain if avg_gain is not None else profit_target
    loss = avg_loss if avg_loss is not None else -stop_loss
    return entry_probability * gain + (1.0 - entry_probability) * loss


def estimate_hold_days(
    avg_trade_duration: float | None = None,
    signal_state: str = SignalState.WATCH,
) -> int:
    """Estimate expected hold days.

    Uses average trade duration from backtests if available,
    otherwise estimates based on signal state.
    """
    if avg_trade_duration is not None and avg_trade_duration > 0:
        return max(1, round(avg_trade_duration))

    defaults: dict[str, int] = {
        SignalState.SIGNAL: 10,
        SignalState.ALERT: 15,
        SignalState.WATCH: 20,
        SignalState.ACTIVE: 8,
        SignalState.TARGET: 3,
    }
    return defaults.get(signal_state, 15)


def generate_forecast(
    signals_data: list[dict[str, object]],
    backtest_data: list[dict[str, object]] | None = None,
    confidence_data: list[dict[str, object]] | None = None,
    factor_weights: dict[str, float] | None = None,
) -> ForecastReport:
    """Generate forecasts for all ETFs from signal, backtest, and confidence data.

    Args:
        signals_data: List of signal dicts from etf.signals output.
        backtest_data: List of backtest result dicts from strategy.backtest-all.
        confidence_data: Not used directly yet; factors extracted from signals.
        factor_weights: Learned factor weights from history.weights.
    """
    date = datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")

    # Build backtest lookup: underlying_ticker -> best result
    bt_lookup: dict[str, dict[str, object]] = {}
    if backtest_data:
        for bt in backtest_data:
            if not isinstance(bt, dict):
                continue
            underlying = str(bt.get("underlying_ticker", ""))
            sharpe = bt.get("sharpe_ratio")
            existing = bt_lookup.get(underlying)
            if existing is None:
                bt_lookup[underlying] = bt
            elif isinstance(sharpe, (int, float)):
                ex_sharpe = existing.get("sharpe_ratio")
                if (
                    not isinstance(ex_sharpe, (int, float))
                    or sharpe > ex_sharpe
                ):
                    bt_lookup[underlying] = bt

    forecasts: list[ETFForecast] = []
    for sig in signals_data:
        if not isinstance(sig, dict):
            continue

        leveraged = str(sig.get("leveraged_ticker", ""))
        underlying = str(sig.get("underlying_ticker", ""))
        state = str(sig.get("state", SignalState.WATCH))
        dd_raw = sig.get("underlying_drawdown_pct", 0)
        drawdown = float(dd_raw) if isinstance(dd_raw, (int, float)) else 0.0

        # Extract factor assessments from signal's confidence data
        factor_scores: dict[str, str] = {}
        confidence_level = str(ConfidenceLevel.LOW)

        # Try to get confidence info from the signal data
        conf = sig.get("confidence")
        if isinstance(conf, dict):
            confidence_level = str(conf.get("level", "LOW"))
            factors = conf.get("factors", [])
            if isinstance(factors, list):
                for f in factors:
                    if isinstance(f, dict):
                        name = str(f.get("name", ""))
                        assessment = str(f.get("assessment", "NEUTRAL"))
                        if name:
                            factor_scores[name] = assessment

        # Get backtest stats for this underlying
        bt = bt_lookup.get(underlying, {})
        win_rate = bt.get("win_rate")
        avg_gain = bt.get("avg_gain")
        avg_loss = bt.get("avg_loss")
        best_strategy = str(bt.get("strategy_type", "ath_mean_reversion"))
        pt_raw = bt.get("profit_target", 0.10)
        profit_target = float(pt_raw) if isinstance(pt_raw, (int, float)) else 0.10

        # Compute avg trade duration from backtest trades
        avg_duration: float | None = None
        bt_trades = bt.get("trades", [])
        if isinstance(bt_trades, list) and bt_trades:
            durations = []
            for t in bt_trades:
                if isinstance(t, dict):
                    entry_d = t.get("entry_day", 0)
                    exit_d = t.get("exit_day", 0)
                    if isinstance(entry_d, (int, float)) and isinstance(
                        exit_d, (int, float)
                    ):
                        durations.append(exit_d - entry_d)
            if durations:
                avg_duration = sum(durations) / len(durations)

        entry_prob = compute_entry_probability(
            signal_state=state,
            factor_assessments=factor_scores,
            backtest_win_rate=(
                float(win_rate)
                if isinstance(win_rate, (int, float))
                else None
            ),
            factor_weights=factor_weights,
        )

        expected_ret = compute_expected_return(
            entry_probability=entry_prob,
            avg_gain=float(avg_gain) if isinstance(avg_gain, (int, float)) else None,
            avg_loss=float(avg_loss) if isinstance(avg_loss, (int, float)) else None,
            profit_target=profit_target,
        )

        hold_days = estimate_hold_days(
            avg_trade_duration=avg_duration,
            signal_state=state,
        )

        forecasts.append(
            ETFForecast(
                leveraged_ticker=leveraged,
                underlying_ticker=underlying,
                signal_state=state,
                current_drawdown_pct=drawdown,
                confidence_level=str(confidence_level),
                entry_probability=round(entry_prob, 4),
                expected_return_pct=round(expected_ret, 4),
                expected_hold_days=hold_days,
                best_strategy=best_strategy,
                factor_scores=factor_scores,
            )
        )

    actionable = sum(1 for f in forecasts if f.entry_probability > 0.50)

    return ForecastReport(
        date=date,
        forecasts=tuple(forecasts),
        actionable_count=actionable,
    )


def save_forecast(report: ForecastReport, path: Path | None = None) -> Path:
    """Save forecast report to JSON."""
    dest = path or (_FORECASTS_DIR / f"{report.date}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )
    return dest


def load_forecast(path: Path) -> ForecastReport:
    """Load forecast report from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    forecasts = tuple(
        ETFForecast(**f) for f in data.get("forecasts", [])
    )
    return ForecastReport(
        date=data["date"],
        forecasts=forecasts,
        actionable_count=data.get("actionable_count", 0),
    )


def list_forecasts() -> list[Path]:
    """List all saved forecast files, newest first."""
    if not _FORECASTS_DIR.exists():
        return []
    return sorted(_FORECASTS_DIR.glob("*.json"), reverse=True)
