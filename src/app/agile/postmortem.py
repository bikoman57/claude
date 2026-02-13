"""Postmortem system: auto-detect failures and generate documentation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.history.outcomes import TradeOutcome, get_completed_outcomes
from app.scheduler.runner import SchedulerRun, load_status

_POSTMORTEMS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "postmortems"
)


@dataclass
class PostmortemItem:
    """A postmortem for a detected failure."""

    id: str  # "PM-2026-02-12-001"
    date: str
    category: str  # "trade_loss", "system_outage", "signal_miss", "pipeline_failure"
    severity: str  # "critical", "major", "minor"
    title: str
    timeline: list[str] = field(default_factory=list)
    root_cause: str = ""
    impact: str = ""
    action_items: list[str] = field(default_factory=list)
    resolved: bool = False
    sprint_number: int | None = None


def detect_failures(
    pipeline_run: SchedulerRun | None = None,
    trade_outcomes: list[TradeOutcome] | None = None,
) -> list[PostmortemItem]:
    """Auto-detect failures that warrant postmortems."""
    if pipeline_run is None:
        pipeline_run = load_status()
    if trade_outcomes is None:
        trade_outcomes = get_completed_outcomes()

    items: list[PostmortemItem] = []
    today = datetime.now(tz=UTC).date().isoformat()
    counter = 1

    # Check for pipeline failures.
    if pipeline_run:
        failed_modules = [r for r in pipeline_run.results if not r.success]

        # System outage: >50% modules failed.
        if len(failed_modules) > len(pipeline_run.results) / 2:
            items.append(
                PostmortemItem(
                    id=f"PM-{today}-{counter:03d}",
                    date=today,
                    category="system_outage",
                    severity="critical",
                    title=(
                        f"System outage: {len(failed_modules)}"
                        f"/{pipeline_run.total_modules} modules failed"
                    ),
                    timeline=[
                        f"Pipeline run started: {pipeline_run.started_at}",
                        f"Failed modules: {', '.join(r.name for r in failed_modules)}",
                    ],
                    impact=f"{len(failed_modules)} data sources unavailable",
                    action_items=["Investigate root cause of widespread failure"],
                ),
            )
            counter += 1

        # Pipeline failures: 2+ consecutive failures of same module.
        elif len(failed_modules) >= 2:
            items.append(
                PostmortemItem(
                    id=f"PM-{today}-{counter:03d}",
                    date=today,
                    category="pipeline_failure",
                    severity="major",
                    title=(
                        f"Pipeline failures: "
                        f"{', '.join(r.name for r in failed_modules)}"
                    ),
                    timeline=[
                        f"Pipeline run: {pipeline_run.started_at}",
                        *[f"{r.name}: {r.error[:100]}" for r in failed_modules],
                    ],
                    impact="Partial data availability",
                    action_items=[
                        f"Fix {r.name}: {r.error[:80]}" for r in failed_modules
                    ],
                ),
            )
            counter += 1

    # Check for significant trade losses.
    recent_outcomes = [
        o
        for o in trade_outcomes
        if o.exit_date and o.exit_date.startswith(today) and o.pl_pct is not None
    ]
    for outcome in recent_outcomes:
        if outcome.pl_pct is not None and outcome.pl_pct < -0.05:
            items.append(
                PostmortemItem(
                    id=f"PM-{today}-{counter:03d}",
                    date=today,
                    category="trade_loss",
                    severity="major",
                    title=(
                        f"Trade loss: {outcome.leveraged_ticker}"
                        f" ({outcome.pl_pct:.1%})"
                    ),
                    timeline=[
                        f"Entry: {outcome.entry_date} at ${outcome.entry_price:.2f}",
                        (
                            f"Exit: {outcome.exit_date} at ${outcome.exit_price:.2f}"
                            if outcome.exit_price
                            else "Exit: pending"
                        ),
                    ],
                    root_cause="Under investigation",
                    impact=(
                        f"Loss of {outcome.pl_pct:.1%}"
                        f" on {outcome.leveraged_ticker}"
                    ),
                    action_items=[
                        "Review entry signal confidence at time of entry",
                        "Check if risk limits were properly enforced",
                    ],
                ),
            )
            counter += 1

    return items


def save_postmortem(
    item: PostmortemItem,
    path: Path | None = None,
) -> Path:
    """Save a postmortem document."""
    base = path or _POSTMORTEMS_DIR
    base.mkdir(parents=True, exist_ok=True)
    file = base / f"{item.id}.json"
    file.write_text(
        json.dumps(asdict(item), indent=2),
        encoding="utf-8",
    )
    return file


def load_postmortems(
    sprint_number: int | None = None,
    *,
    path: Path | None = None,
) -> list[PostmortemItem]:
    """Load postmortems, optionally filtered by sprint."""
    base = path or _POSTMORTEMS_DIR
    if not base.exists():
        return []
    items: list[PostmortemItem] = []
    for file in sorted(base.glob("PM-*.json")):
        raw = json.loads(file.read_text(encoding="utf-8"))
        item = PostmortemItem(**raw)
        if sprint_number is None or item.sprint_number == sprint_number:
            items.append(item)
    return items


def weekly_postmortem_summary(
    sprint_number: int,
    *,
    path: Path | None = None,
) -> str:
    """Generate summary for sprint retro."""
    items = load_postmortems(sprint_number, path=path)
    if not items:
        return "No postmortems this sprint."

    by_severity = {"critical": 0, "major": 0, "minor": 0}
    for item in items:
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1

    resolved = sum(1 for i in items if i.resolved)
    lines = [
        f"Postmortems: {len(items)} total ({resolved} resolved)",
        (
            f"  Critical: {by_severity['critical']},"
            f" Major: {by_severity['major']},"
            f" Minor: {by_severity['minor']}"
        ),
    ]
    for item in items[:5]:
        status = "RESOLVED" if item.resolved else "OPEN"
        lines.append(f"  [{status}] {item.title}")
    return "\n".join(lines)
