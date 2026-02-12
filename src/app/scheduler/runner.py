"""Scheduler runner: execute all module CLIs in sequence."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_STATUS_PATH = Path("data/scheduler_status.json")

# Each module CLI command to run, in order
MODULE_COMMANDS: list[tuple[str, list[str]]] = [
    ("etf.signals", [sys.executable, "-m", "app.etf", "signals"]),
    ("etf.active", [sys.executable, "-m", "app.etf", "active"]),
    ("macro.dashboard", [sys.executable, "-m", "app.macro", "dashboard"]),
    ("macro.yields", [sys.executable, "-m", "app.macro", "yields"]),
    ("macro.rates", [sys.executable, "-m", "app.macro", "rates"]),
    ("macro.calendar", [sys.executable, "-m", "app.macro", "calendar"]),
    ("sec.recent", [sys.executable, "-m", "app.sec", "recent"]),
    (
        "sec.institutional",
        [sys.executable, "-m", "app.sec", "institutional"],
    ),
    (
        "geopolitical.summary",
        [sys.executable, "-m", "app.geopolitical", "summary"],
    ),
    ("social.summary", [sys.executable, "-m", "app.social", "summary"]),
    ("news.summary", [sys.executable, "-m", "app.news", "summary"]),
    (
        "statistics.dashboard",
        [sys.executable, "-m", "app.statistics", "dashboard"],
    ),
    (
        "strategy.proposals",
        [sys.executable, "-m", "app.strategy", "proposals"],
    ),
    (
        "strategy.backtest-all",
        [sys.executable, "-m", "app.strategy", "backtest-all"],
    ),
    (
        "strategy.forecast",
        [sys.executable, "-m", "app.strategy", "forecast"],
    ),
    (
        "strategy.verify",
        [sys.executable, "-m", "app.strategy", "verify"],
    ),
    (
        "congress.summary",
        [sys.executable, "-m", "app.congress", "summary"],
    ),
    (
        "history.weights",
        [sys.executable, "-m", "app.history", "weights"],
    ),
    (
        "history.summary",
        [sys.executable, "-m", "app.history", "summary"],
    ),
]


@dataclass
class ModuleResult:
    """Result of running one module CLI."""

    name: str
    success: bool
    output: str
    error: str
    duration_seconds: float


@dataclass
class SchedulerRun:
    """Full scheduler run result."""

    started_at: str
    finished_at: str
    results: list[ModuleResult] = field(default_factory=list)
    total_modules: int = 0
    succeeded: int = 0
    failed: int = 0


def run_module(
    name: str,
    command: list[str],
    timeout: int = 120,
) -> ModuleResult:
    """Run a single module CLI command."""
    start = datetime.now(tz=UTC)
    try:
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = (datetime.now(tz=UTC) - start).total_seconds()
        return ModuleResult(
            name=name,
            success=result.returncode == 0,
            output=result.stdout[:500_000],
            error=result.stderr[:5000],
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired:
        duration = (datetime.now(tz=UTC) - start).total_seconds()
        return ModuleResult(
            name=name,
            success=False,
            output="",
            error=f"Timed out after {timeout}s",
            duration_seconds=duration,
        )
    except Exception as exc:
        duration = (datetime.now(tz=UTC) - start).total_seconds()
        return ModuleResult(
            name=name,
            success=False,
            output="",
            error=str(exc),
            duration_seconds=duration,
        )


def run_all_modules(
    commands: list[tuple[str, list[str]]] | None = None,
    timeout: int = 120,
) -> SchedulerRun:
    """Run all module CLIs in sequence, continuing on failure."""
    cmds = commands if commands is not None else MODULE_COMMANDS
    started = datetime.now(tz=UTC).isoformat(timespec="seconds")

    results: list[ModuleResult] = []
    for name, cmd in cmds:
        result = run_module(name, cmd, timeout=timeout)
        results.append(result)

    finished = datetime.now(tz=UTC).isoformat(timespec="seconds")
    succeeded = sum(1 for r in results if r.success)

    run = SchedulerRun(
        started_at=started,
        finished_at=finished,
        results=results,
        total_modules=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
    )

    _save_status(run)
    return run


def _save_status(run: SchedulerRun) -> None:
    """Save scheduler run status to JSON."""
    _STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATUS_PATH.write_text(json.dumps(asdict(run), indent=2))


def load_status() -> SchedulerRun | None:
    """Load last scheduler run status."""
    if not _STATUS_PATH.exists():
        return None
    data = json.loads(_STATUS_PATH.read_text())
    results = [ModuleResult(**r) for r in data.pop("results", [])]
    return SchedulerRun(results=results, **data)
