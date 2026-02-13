"""Ceremony generation logic: standups, planning, reviews, retrospectives."""

from __future__ import annotations

from datetime import UTC, datetime

from app.agile.models import (
    OKR,
    RetroItem,
    RetroRecord,
    Sprint,
    SprintTask,
    StandupEntry,
    StandupRecord,
    TaskPriority,
    TaskStatus,
)
from app.agile.store import (
    load_roadmap,
    save_standup,
)
from app.scheduler.runner import SchedulerRun, load_status


def generate_standup(
    sprint: Sprint,
    session: str,
    pipeline_run: SchedulerRun | None = None,
) -> StandupRecord:
    """Generate a standup from current system state.

    Each department contributes an entry based on pipeline and signal data.
    """
    if pipeline_run is None:
        pipeline_run = load_status()

    entries: list[StandupEntry] = []
    now = datetime.now(tz=UTC).isoformat(timespec="seconds")

    # Trading department.
    entries.append(
        StandupEntry(
            department="trading",
            agent="trading-swing-screener",
            yesterday=_module_summary(pipeline_run, "etf."),
            today="Scan for entry/exit signals, monitor drawdowns",
            blockers="",
        ),
    )

    # Research department.
    entries.append(
        StandupEntry(
            department="research",
            agent="research-macro",
            yesterday=_module_summary(pipeline_run, "macro."),
            today="Analyze macro conditions, strategy proposals",
            blockers="",
        ),
    )

    # Intelligence department.
    entries.append(
        StandupEntry(
            department="intelligence",
            agent="intel-chief",
            yesterday=_module_summary(
                pipeline_run,
                "geopolitical.",
                "social.",
                "news.",
                "congress.",
            ),
            today="Aggregate sentiment across all sources",
            blockers="",
        ),
    )

    # Risk department.
    entries.append(
        StandupEntry(
            department="risk",
            agent="risk-manager",
            yesterday=_module_summary(pipeline_run, "risk.", "portfolio."),
            today="Monitor portfolio limits, evaluate veto triggers",
            blockers="",
        ),
    )

    # Operations department.
    failed_modules = _failed_modules(pipeline_run)
    failed_str = ", ".join(failed_modules)
    ops_blockers = f"Failed modules: {failed_str}" if failed_modules else ""
    entries.append(
        StandupEntry(
            department="operations",
            agent="exec-coo",
            yesterday=_pipeline_health_summary(pipeline_run),
            today="Monitor system health, data freshness",
            blockers=ops_blockers,
        ),
    )

    record = StandupRecord(
        date=datetime.now(tz=UTC).date().isoformat(),
        sprint_number=sprint.number,
        session=session,
        entries=entries,
        summary=_standup_summary(entries, sprint),
        generated_at=now,
    )
    save_standup(record)
    return record


def generate_planning(
    previous_sprint: Sprint | None,
    roadmap_okrs: list[OKR] | None = None,
) -> list[SprintTask]:
    """Generate tasks for a new sprint from retro action items + roadmap OKRs."""
    tasks: list[SprintTask] = []
    task_num = 1

    if roadmap_okrs is None:
        roadmap = load_roadmap()
        roadmap_okrs = [o for o in roadmap.okrs if o.status == "active"]

    # Carry over incomplete tasks from previous sprint.
    if previous_sprint:
        for task in previous_sprint.tasks:
            if task.status not in (TaskStatus.DONE, TaskStatus.TODO):
                tasks.append(
                    SprintTask(
                        id=f"S?-T{task_num}",
                        title=f"[Carry-over] {task.title}",
                        description=task.description,
                        assignee_department=task.assignee_department,
                        priority=task.priority,
                        created_date=datetime.now(tz=UTC).date().isoformat(),
                        notes=f"Carried from Sprint {previous_sprint.number}",
                    ),
                )
                task_num += 1

    # Generate tasks from active OKRs.
    for okr in roadmap_okrs:
        for kr in okr.key_results:
            if okr.progress_pct < 100:
                dept = _okr_department(okr.id)
                tasks.append(
                    SprintTask(
                        id=f"S?-T{task_num}",
                        title=f"Progress on: {kr[:60]}",
                        description=f"OKR {okr.id}: {okr.objective}",
                        assignee_department=dept,
                        priority=TaskPriority.MEDIUM,
                        created_date=datetime.now(tz=UTC).date().isoformat(),
                    ),
                )
                task_num += 1
                break  # One task per OKR per sprint.

    return tasks


def generate_retro(
    sprint: Sprint,
    token_spend: float = 0.0,
    trading_summary: str = "",
    pipeline_success_rate: float = 0.0,
) -> RetroRecord:
    """Generate a retrospective from sprint data."""
    went_well: list[RetroItem] = []
    to_improve: list[RetroItem] = []
    action_items: list[RetroItem] = []

    done = sum(1 for t in sprint.tasks if t.status == TaskStatus.DONE)
    total = len(sprint.tasks)

    # Went well.
    if total > 0 and done / total >= 0.8:
        went_well.append(
            RetroItem("went_well", f"High velocity: {done}/{total} tasks completed"),
        )
    if pipeline_success_rate >= 95:
        went_well.append(
            RetroItem(
                "went_well",
                f"Pipeline reliability: {pipeline_success_rate:.0f}%",
            ),
        )
    if not went_well:
        went_well.append(RetroItem("went_well", "Sprint completed on schedule"))

    # To improve.
    if total > 0 and done / total < 0.5:
        to_improve.append(
            RetroItem(
                "improve",
                f"Low velocity: only {done}/{total} tasks completed",
                priority=TaskPriority.HIGH,
            ),
        )
    if pipeline_success_rate < 90:
        to_improve.append(
            RetroItem(
                "improve",
                f"Pipeline reliability below target: {pipeline_success_rate:.0f}%",
                priority=TaskPriority.HIGH,
            ),
        )

    # Blocked tasks become action items.
    for task in sprint.tasks:
        if task.status == TaskStatus.BLOCKED:
            action_items.append(
                RetroItem(
                    "action_item",
                    f"Unblock: {task.title}",
                    department=task.assignee_department,
                    priority=TaskPriority.HIGH,
                ),
            )

    return RetroRecord(
        sprint_number=sprint.number,
        date=datetime.now(tz=UTC).date().isoformat(),
        went_well=went_well,
        to_improve=to_improve,
        action_items=action_items,
        velocity=done,
        token_spend_total=token_spend,
        trading_outcomes=trading_summary,
        generated_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _module_summary(run: SchedulerRun | None, *prefixes: str) -> str:
    """Summarize module results matching prefixes."""
    if run is None:
        return "No pipeline data available"
    matching = [r for r in run.results if any(r.name.startswith(p) for p in prefixes)]
    if not matching:
        return "No relevant modules ran"
    ok = sum(1 for r in matching if r.success)
    return f"{ok}/{len(matching)} modules OK"


def _failed_modules(run: SchedulerRun | None) -> list[str]:
    """Get names of failed modules."""
    if run is None:
        return []
    return [r.name for r in run.results if not r.success]


def _pipeline_health_summary(run: SchedulerRun | None) -> str:
    """Summarize pipeline health."""
    if run is None:
        return "No pipeline run data"
    return f"Pipeline: {run.succeeded}/{run.total_modules} OK, {run.failed} failed"


def _standup_summary(entries: list[StandupEntry], sprint: Sprint) -> str:
    """Create a one-line standup summary."""
    blockers = [e for e in entries if e.blockers]
    blocker_text = f", {len(blockers)} blockers" if blockers else ""
    done = sum(1 for t in sprint.tasks if t.status == TaskStatus.DONE)
    n = sprint.number
    total = len(sprint.tasks)
    return f"Sprint {n}: {done}/{total} tasks done{blocker_text}"


def _okr_department(okr_id: str) -> str:
    """Map OKR to responsible department."""
    mapping: dict[str, str] = {
        "OKR-1": "trading",
        "OKR-2": "operations",
        "OKR-3": "intelligence",
    }
    return mapping.get(okr_id, "research")
