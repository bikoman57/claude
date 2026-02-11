from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.etf.universe import ETF_UNIVERSE, ETFMapping
from app.strategy.backtest import BacktestConfig, BacktestResult, run_backtest

_THRESHOLDS = [0.03, 0.05, 0.07, 0.10, 0.12, 0.15]
_PROFIT_TARGETS = [0.08, 0.10, 0.15]
_STOP_LOSS = 0.15
_PERIOD = "2y"


@dataclass(frozen=True, slots=True)
class PerETFBreakdown:
    """Backtest results across thresholds for one ETF."""

    mapping: ETFMapping
    results: tuple[BacktestResult, ...]
    best_result: BacktestResult | None
    best_threshold: float | None
    best_target: float | None


@dataclass(frozen=True, slots=True)
class StrategyProposal:
    """Proposed strategy change based on backtest results."""

    leveraged_ticker: str
    current_threshold: float
    proposed_threshold: float
    current_target: float
    proposed_target: float
    improvement_reason: str
    backtest_sharpe: float | None
    backtest_win_rate: float | None
    backtest_total_return: float


@dataclass(frozen=True, slots=True)
class ProposalsSummary:
    """Full set of strategy proposals."""

    breakdowns: tuple[PerETFBreakdown, ...]
    proposals: tuple[StrategyProposal, ...]
    as_of: str


def optimize_single_etf(
    mapping: ETFMapping,
    period: str = _PERIOD,
) -> PerETFBreakdown:
    """Test multiple thresholds and targets for one ETF."""
    results: list[BacktestResult] = []

    for threshold in _THRESHOLDS:
        for target in _PROFIT_TARGETS:
            config = BacktestConfig(
                underlying_ticker=mapping.underlying_ticker,
                leverage=mapping.leverage,
                entry_threshold=threshold,
                profit_target=target,
                stop_loss=_STOP_LOSS,
                period=period,
            )
            result = run_backtest(config)
            if result is not None and result.trades:
                results.append(result)

    # Find best by Sharpe ratio, falling back to win rate
    best: BacktestResult | None = None
    for r in results:
        if best is None:
            best = r
            continue
        r_sharpe = r.sharpe_ratio if r.sharpe_ratio is not None else -999.0
        b_sharpe = (
            best.sharpe_ratio if best.sharpe_ratio is not None else -999.0
        )
        if r_sharpe > b_sharpe:
            best = r

    return PerETFBreakdown(
        mapping=mapping,
        results=tuple(results),
        best_result=best,
        best_threshold=(
            best.config.entry_threshold if best is not None else None
        ),
        best_target=(
            best.config.profit_target if best is not None else None
        ),
    )


def _make_proposal(
    mapping: ETFMapping,
    breakdown: PerETFBreakdown,
) -> StrategyProposal | None:
    """Generate a proposal if backtest suggests different parameters."""
    best = breakdown.best_result
    if best is None:
        return None

    threshold_diff = abs(
        best.config.entry_threshold - mapping.drawdown_threshold,
    )
    target_diff = abs(best.config.profit_target - mapping.profit_target)

    # Only propose if meaningfully different
    if threshold_diff < 0.005 and target_diff < 0.005:
        return None

    reasons: list[str] = []
    if threshold_diff >= 0.005:
        reasons.append(
            f"entry {best.config.entry_threshold:.0%} vs "
            f"current {mapping.drawdown_threshold:.0%}",
        )
    if target_diff >= 0.005:
        reasons.append(
            f"target {best.config.profit_target:.0%} vs "
            f"current {mapping.profit_target:.0%}",
        )

    sharpe_str = (
        f"Sharpe={best.sharpe_ratio:.2f}"
        if best.sharpe_ratio is not None
        else "Sharpe=N/A"
    )
    reason = f"Backtest ({sharpe_str}): " + ", ".join(reasons)

    return StrategyProposal(
        leveraged_ticker=mapping.leveraged_ticker,
        current_threshold=mapping.drawdown_threshold,
        proposed_threshold=best.config.entry_threshold,
        current_target=mapping.profit_target,
        proposed_target=best.config.profit_target,
        improvement_reason=reason,
        backtest_sharpe=best.sharpe_ratio,
        backtest_win_rate=best.win_rate,
        backtest_total_return=best.total_return,
    )


def generate_proposals(
    period: str = _PERIOD,
) -> ProposalsSummary:
    """Run optimization across all tracked ETFs and generate proposals."""
    breakdowns: list[PerETFBreakdown] = []
    proposals: list[StrategyProposal] = []

    for mapping in ETF_UNIVERSE:
        breakdown = optimize_single_etf(mapping, period=period)
        breakdowns.append(breakdown)

        proposal = _make_proposal(mapping, breakdown)
        if proposal is not None:
            proposals.append(proposal)

    return ProposalsSummary(
        breakdowns=tuple(breakdowns),
        proposals=tuple(proposals),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
