from __future__ import annotations

from unittest.mock import patch

from app.etf.universe import ETFMapping
from app.strategy.backtest import (
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    StrategyType,
)
from app.strategy.proposals import (
    PerETFBreakdown,
    StrategyProposal,
    _make_proposal,
    optimize_single_etf,
)


def _make_mapping(**overrides) -> ETFMapping:
    defaults = {
        "leveraged_ticker": "TQQQ",
        "underlying_ticker": "QQQ",
        "name": "Nasdaq-100 3x Bull",
        "leverage": 3.0,
        "drawdown_threshold": 0.05,
        "alert_threshold": 0.03,
        "profit_target": 0.10,
    }
    defaults.update(overrides)
    return ETFMapping(**defaults)


def _make_result(
    threshold: float = 0.05,
    target: float = 0.10,
    sharpe: float | None = 1.5,
    win_rate: float | None = 0.7,
    total_return: float = 0.25,
    trade_count: int = 5,
    strategy_type: str = StrategyType.ATH_MEAN_REVERSION,
    weighted_sharpe: float | None = None,
    weighted_win_rate: float | None = None,
) -> BacktestResult:
    config = BacktestConfig(
        underlying_ticker="QQQ",
        leverage=3.0,
        entry_threshold=threshold,
        profit_target=target,
        stop_loss=0.15,
        period="15y",
        strategy_type=strategy_type,
    )
    trades = tuple(
        BacktestTrade(
            entry_day=i * 20,
            exit_day=i * 20 + 10,
            entry_price=100.0,
            exit_price=105.0,
            drawdown_at_entry=threshold,
            leveraged_return=0.05,
            exit_reason="target",
        )
        for i in range(trade_count)
    )
    return BacktestResult(
        config=config,
        trades=trades,
        total_return=total_return,
        sharpe_ratio=sharpe,
        max_drawdown=0.10,
        win_rate=win_rate,
        avg_gain=0.08,
        avg_loss=-0.03,
        total_days=500,
        weighted_sharpe_ratio=(
            weighted_sharpe if weighted_sharpe is not None else sharpe
        ),
        weighted_win_rate=(
            weighted_win_rate if weighted_win_rate is not None else win_rate
        ),
    )


def test_proposal_dataclass():
    p = StrategyProposal(
        leveraged_ticker="TQQQ",
        strategy_type="ath_mean_reversion",
        strategy_description="Buy when underlying draws down from ATH",
        threshold_label="drawdown %",
        current_threshold=0.05,
        proposed_threshold=0.07,
        current_target=0.10,
        proposed_target=0.15,
        improvement_reason="test",
        backtest_sharpe=1.5,
        backtest_win_rate=0.7,
        backtest_total_return=0.25,
        backtest_trade_count=5,
        backtest_max_drawdown=0.10,
        backtest_total_days=500,
        backtest_avg_gain=0.08,
        backtest_avg_loss=-0.03,
        backtest_period="15y",
    )
    assert p.proposed_threshold == 0.07
    assert p.strategy_type == "ath_mean_reversion"


def test_per_etf_breakdown_dataclass():
    result = _make_result()
    breakdown = PerETFBreakdown(
        mapping=_make_mapping(),
        results=(result,),
        best_result=result,
        best_threshold=0.05,
        best_target=0.10,
        best_strategy_type="ath_mean_reversion",
    )
    assert breakdown.best_threshold == 0.05
    assert len(breakdown.results) == 1
    assert breakdown.best_strategy_type == "ath_mean_reversion"


def test_make_proposal_no_change():
    """Same parameters → no proposal."""
    mapping = _make_mapping(drawdown_threshold=0.05, profit_target=0.10)
    result = _make_result(threshold=0.05, target=0.10)
    breakdown = PerETFBreakdown(
        mapping=mapping,
        results=(result,),
        best_result=result,
        best_threshold=0.05,
        best_target=0.10,
        best_strategy_type="ath_mean_reversion",
    )
    proposal = _make_proposal(mapping, breakdown)
    assert proposal is None


def test_make_proposal_different_threshold():
    """Different threshold → proposal generated."""
    mapping = _make_mapping(drawdown_threshold=0.05, profit_target=0.10)
    result = _make_result(threshold=0.07, target=0.10, sharpe=1.8)
    breakdown = PerETFBreakdown(
        mapping=mapping,
        results=(result,),
        best_result=result,
        best_threshold=0.07,
        best_target=0.10,
        best_strategy_type="ath_mean_reversion",
    )
    proposal = _make_proposal(mapping, breakdown)
    assert proposal is not None
    assert proposal.proposed_threshold == 0.07
    assert "drawdown" in proposal.improvement_reason


def test_make_proposal_different_target():
    """Different profit target → proposal generated."""
    mapping = _make_mapping(drawdown_threshold=0.05, profit_target=0.10)
    result = _make_result(threshold=0.05, target=0.15)
    breakdown = PerETFBreakdown(
        mapping=mapping,
        results=(result,),
        best_result=result,
        best_threshold=0.05,
        best_target=0.15,
        best_strategy_type="ath_mean_reversion",
    )
    proposal = _make_proposal(mapping, breakdown)
    assert proposal is not None
    assert proposal.proposed_target == 0.15
    assert "target" in proposal.improvement_reason


def test_make_proposal_different_strategy():
    """Different strategy type → proposal generated even if params same."""
    mapping = _make_mapping(drawdown_threshold=0.05, profit_target=0.10)
    result = _make_result(
        threshold=30.0,
        target=0.10,
        sharpe=2.0,
        strategy_type=StrategyType.RSI_OVERSOLD,
    )
    breakdown = PerETFBreakdown(
        mapping=mapping,
        results=(result,),
        best_result=result,
        best_threshold=30.0,
        best_target=0.10,
        best_strategy_type="rsi_oversold",
    )
    proposal = _make_proposal(mapping, breakdown)
    assert proposal is not None
    assert proposal.strategy_type == "rsi_oversold"
    assert "RSI" in proposal.threshold_label


def test_make_proposal_no_best():
    """No best result → no proposal."""
    mapping = _make_mapping()
    breakdown = PerETFBreakdown(
        mapping=mapping,
        results=(),
        best_result=None,
        best_threshold=None,
        best_target=None,
        best_strategy_type=None,
    )
    proposal = _make_proposal(mapping, breakdown)
    assert proposal is None


@patch("app.strategy.proposals.run_backtest")
def test_optimize_single_etf(mock_run):
    """Test optimization picks best Sharpe across strategies."""
    low_sharpe = _make_result(threshold=0.03, sharpe=0.5)
    high_sharpe = _make_result(
        threshold=30.0,
        sharpe=2.5,
        strategy_type=StrategyType.RSI_OVERSOLD,
    )

    results_iter = iter([low_sharpe, high_sharpe] + [None] * 100)
    mock_run.side_effect = lambda cfg: next(results_iter)

    mapping = _make_mapping()
    breakdown = optimize_single_etf(mapping)

    assert breakdown.best_result is not None
    assert breakdown.best_result.sharpe_ratio == 2.5
    assert breakdown.best_strategy_type == "rsi_oversold"


@patch("app.strategy.proposals.run_backtest")
def test_optimize_all_none(mock_run):
    """All backtests fail → no best result."""
    mock_run.return_value = None
    mapping = _make_mapping()
    breakdown = optimize_single_etf(mapping)

    assert breakdown.best_result is None
    assert breakdown.best_threshold is None
    assert breakdown.best_strategy_type is None
    assert len(breakdown.results) == 0


@patch("app.strategy.proposals.run_backtest")
def test_optimize_prefers_weighted_sharpe(mock_run):
    """Optimizer selects by weighted Sharpe, not raw Sharpe."""
    # Higher raw Sharpe but lower weighted Sharpe (old trades inflating it)
    old_biased = _make_result(
        threshold=0.05,
        sharpe=3.0,
        weighted_sharpe=0.8,
    )
    # Lower raw Sharpe but higher weighted Sharpe (recent trades doing well)
    recent_biased = _make_result(
        threshold=30.0,
        sharpe=1.5,
        weighted_sharpe=2.0,
        strategy_type=StrategyType.RSI_OVERSOLD,
    )

    results_iter = iter([old_biased, recent_biased] + [None] * 100)
    mock_run.side_effect = lambda cfg: next(results_iter)

    mapping = _make_mapping()
    breakdown = optimize_single_etf(mapping)

    assert breakdown.best_result is not None
    # Should pick the one with higher weighted Sharpe
    assert breakdown.best_result.weighted_sharpe_ratio == 2.0
    assert breakdown.best_strategy_type == "rsi_oversold"
