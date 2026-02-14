from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.strategy.backtest import (
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
)

_DATA_DIR = Path("data/backtests")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_backtest(result: BacktestResult) -> Path:
    """Save a backtest result to JSON file."""
    _ensure_dir()
    ticker = result.config.underlying_ticker
    date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    threshold = f"{result.config.entry_threshold:.0%}".replace("%", "")
    filename = f"{ticker}_{threshold}pct_{date}.json"
    path = _DATA_DIR / filename

    data = asdict(result)
    path.write_text(json.dumps(data, indent=2))
    return path


def load_backtest(path: Path) -> BacktestResult:
    """Load a backtest result from JSON file."""
    data = json.loads(path.read_text())

    config = BacktestConfig(**data["config"])
    trades = tuple(
        BacktestTrade(
            entry_day=t["entry_day"],
            exit_day=t["exit_day"],
            entry_price=t["entry_price"],
            exit_price=t["exit_price"],
            drawdown_at_entry=t["drawdown_at_entry"],
            leveraged_return=t["leveraged_return"],
            exit_reason=t["exit_reason"],
            entry_date=t.get("entry_date", ""),
            exit_date=t.get("exit_date", ""),
        )
        for t in data["trades"]
    )

    return BacktestResult(
        config=config,
        trades=trades,
        total_return=data["total_return"],
        sharpe_ratio=data["sharpe_ratio"],
        max_drawdown=data["max_drawdown"],
        win_rate=data["win_rate"],
        avg_gain=data["avg_gain"],
        avg_loss=data["avg_loss"],
        total_days=data["total_days"],
        weighted_sharpe_ratio=data.get("weighted_sharpe_ratio"),
        weighted_win_rate=data.get("weighted_win_rate"),
    )


def list_backtests(ticker: str | None = None) -> list[Path]:
    """List saved backtest files, optionally filtered by ticker."""
    if not _DATA_DIR.exists():
        return []
    files = sorted(_DATA_DIR.glob("*.json"))
    if ticker is not None:
        files = [f for f in files if f.name.startswith(f"{ticker}_")]
    return files
