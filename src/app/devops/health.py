"""Pipeline health tracking, trend analysis, and system scoring."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.devops.models import ModuleHealth, PipelineHistory, SystemHealthScore
from app.scheduler.runner import SchedulerRun

_DEVOPS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "devops"
_HISTORY_PATH = _DEVOPS_DIR / "pipeline_history.json"


def record_pipeline_run(
    run: SchedulerRun,
    session: str,
    *,
    path: Path | None = None,
) -> PipelineHistory:
    """Record a pipeline run for trend analysis."""
    entry = PipelineHistory(
        date=datetime.now(tz=UTC).date().isoformat(),
        session=session,
        modules_ok=run.succeeded,
        modules_total=run.total_modules,
        duration_seconds=sum(r.duration_seconds for r in run.results),
        module_results={r.name: r.success for r in run.results},
    )
    store = path or _HISTORY_PATH
    store.parent.mkdir(parents=True, exist_ok=True)

    history: list[dict[str, object]] = []
    if store.exists():
        history = json.loads(store.read_text(encoding="utf-8"))
    history.append(asdict(entry))

    # Keep last 90 days max.
    cutoff = (datetime.now(tz=UTC).date() - timedelta(days=90)).isoformat()
    history = [h for h in history if str(h.get("date", "")) >= cutoff]

    store.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return entry


def load_pipeline_history(
    days: int = 7,
    *,
    path: Path | None = None,
) -> list[PipelineHistory]:
    """Load pipeline history for the last N days."""
    store = path or _HISTORY_PATH
    if not store.exists():
        return []
    raw: list[dict[str, object]] = json.loads(store.read_text(encoding="utf-8"))
    cutoff = (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()
    entries = []
    for r in raw:
        if str(r.get("date", "")) >= cutoff:
            entries.append(PipelineHistory(**r))  # type: ignore[arg-type]
    return entries


def get_module_health(
    module_name: str,
    days: int = 7,
    *,
    path: Path | None = None,
) -> ModuleHealth:
    """Calculate health for a single module over N days."""
    history = load_pipeline_history(days, path=path)
    runs_with_module = [h for h in history if module_name in h.module_results]
    if not runs_with_module:
        return ModuleHealth(
            name=module_name,
            success_rate_7d=0.0,
            avg_duration_seconds=0.0,
            trend="unknown",
            last_failure=None,
            failure_reason=None,
        )

    successes = sum(
        1 for h in runs_with_module if h.module_results.get(module_name, False)
    )
    rate = successes / len(runs_with_module) * 100

    # Trend: compare first half vs second half success rate.
    mid = len(runs_with_module) // 2
    if mid > 0:
        first_half_rate = (
            sum(1 for h in runs_with_module[:mid] if h.module_results.get(module_name))
            / mid
        )
        second_half_rate = sum(
            1 for h in runs_with_module[mid:] if h.module_results.get(module_name)
        ) / (len(runs_with_module) - mid)
        if second_half_rate > first_half_rate + 0.1:
            trend = "improving"
        elif second_half_rate < first_half_rate - 0.1:
            trend = "degrading"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Last failure.
    last_failure = None
    failure_reason = None
    for h in reversed(runs_with_module):
        if not h.module_results.get(module_name, True):
            last_failure = h.date
            break

    return ModuleHealth(
        name=module_name,
        success_rate_7d=round(rate, 1),
        avg_duration_seconds=0.0,  # Duration is aggregate, not per-module.
        trend=trend,
        last_failure=last_failure,
        failure_reason=failure_reason,
    )


def get_all_module_health(
    days: int = 7,
    *,
    path: Path | None = None,
) -> list[ModuleHealth]:
    """Get health for all known modules."""
    history = load_pipeline_history(days, path=path)
    module_names: set[str] = set()
    for h in history:
        module_names.update(h.module_results.keys())

    return [get_module_health(name, days, path=path) for name in sorted(module_names)]


def get_system_health(
    days: int = 7,
    *,
    path: Path | None = None,
) -> SystemHealthScore:
    """Calculate overall system health score."""
    history = load_pipeline_history(days, path=path)
    if not history:
        return SystemHealthScore(
            score=0.0,
            grade="F",
            pipeline_health=0.0,
            data_freshness=0.0,
            module_count=0,
            details=("No pipeline history available",),
        )

    # Pipeline health: average success rate across all runs.
    total_ok = sum(h.modules_ok for h in history)
    total_modules = sum(h.modules_total for h in history)
    pipeline_health = total_ok / total_modules if total_modules > 0 else 0.0

    # Data freshness: how recent is the last run.
    latest = max(h.date for h in history)
    days_since = (datetime.now(tz=UTC).date() - date.fromisoformat(latest)).days
    freshness = max(0.0, 1.0 - days_since * 0.2)  # Degrades 20% per day.

    # Combined score (70% pipeline + 30% freshness).
    score = pipeline_health * 0.7 + freshness * 0.3

    grade = _score_to_grade(score)

    module_names: set[str] = set()
    for h in history:
        module_names.update(h.module_results.keys())

    details: list[str] = []
    if pipeline_health < 0.9:
        details.append(f"Pipeline success rate: {pipeline_health:.0%}")
    if days_since > 1:
        details.append(f"Last run: {days_since} days ago")

    return SystemHealthScore(
        score=round(score, 3),
        grade=grade,
        pipeline_health=round(pipeline_health, 3),
        data_freshness=round(freshness, 3),
        module_count=len(module_names),
        details=tuple(details),
    )


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 0.9:
        return "A"
    if score >= 0.8:
        return "B"
    if score >= 0.7:
        return "C"
    if score >= 0.6:
        return "D"
    return "F"
