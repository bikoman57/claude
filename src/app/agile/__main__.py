"""Agile CLI.

Usage:
    python -m app.agile sprint         Show current sprint
    python -m app.agile standup        Show today's standup
    python -m app.agile planning       Show sprint planning info
    python -m app.agile review         Show sprint review summary
    python -m app.agile retro          Show sprint retrospective
    python -m app.agile roadmap        Show company roadmap
    python -m app.agile init           Initialize Sprint 1 + roadmap
    python -m app.agile advance        Advance to next sprint
    python -m app.agile tasks          List current sprint tasks
"""

from __future__ import annotations

import sys

from app.agile.models import SprintStatus, TaskStatus
from app.agile.store import (
    advance_sprint,
    get_current_sprint,
    init_agile,
    list_retros,
    list_standups,
    load_retro,
    load_roadmap,
    load_sprints,
    load_standup,
)


def _cmd_sprint() -> int:
    sprint = get_current_sprint()
    if sprint is None:
        print("No active sprint. Run: python -m app.agile init")  # noqa: T201
        return 1

    done = sum(1 for t in sprint.tasks if t.status == TaskStatus.DONE)
    total = len(sprint.tasks)

    print(f"=== Sprint {sprint.number} ({sprint.status}) ===")  # noqa: T201
    print(f"Period: {sprint.start_date} to {sprint.end_date}")  # noqa: T201
    print(f"Tasks: {done}/{total} completed")  # noqa: T201
    if sprint.goals:
        print("\nGoals:")  # noqa: T201
        for g in sprint.goals:
            print(f"  - {g}")  # noqa: T201
    return 0


def _cmd_standup() -> int:
    from datetime import UTC, datetime

    today = datetime.now(tz=UTC).date().isoformat()
    record = load_standup(today)
    if record is None:
        print(f"No standup recorded for {today}.")  # noqa: T201
        dates = list_standups()
        if dates:
            print(f"Recent standups: {', '.join(dates[-5:])}")  # noqa: T201
        return 0

    print(f"=== Standup {record.date} (Sprint {record.sprint_number}) ===")  # noqa: T201
    for entry in record.entries:
        print(f"\n[{entry.department}] {entry.agent}")  # noqa: T201
        print(f"  Yesterday: {entry.yesterday}")  # noqa: T201
        print(f"  Today:     {entry.today}")  # noqa: T201
        if entry.blockers:
            print(f"  Blockers:  {entry.blockers}")  # noqa: T201
    if record.summary:
        print(f"\nSummary: {record.summary}")  # noqa: T201
    return 0


def _cmd_planning() -> int:
    sprint = get_current_sprint()
    if sprint is None:
        print("No active sprint.")  # noqa: T201
        return 1

    roadmap = load_roadmap()
    print(f"=== Sprint {sprint.number} Planning ===")  # noqa: T201
    print(f"Period: {sprint.start_date} to {sprint.end_date}")  # noqa: T201
    print(f"Goals: {len(sprint.goals)}")  # noqa: T201
    print(f"Tasks: {len(sprint.tasks)}")  # noqa: T201

    active_okrs = [o for o in roadmap.okrs if o.status == "active"]
    if active_okrs:
        print(f"\nActive OKRs: {len(active_okrs)}")  # noqa: T201
        for okr in active_okrs:
            print(f"  [{okr.id}] {okr.objective} ({okr.progress_pct:.0f}%)")  # noqa: T201
    return 0


def _cmd_review() -> int:
    sprint = get_current_sprint()
    if sprint is None:
        sprints = load_sprints()
        completed = [s for s in sprints if s.status == SprintStatus.COMPLETED]
        if completed:
            sprint = completed[-1]
        else:
            print("No sprint to review.")  # noqa: T201
            return 1

    done = sum(1 for t in sprint.tasks if t.status == TaskStatus.DONE)
    total = len(sprint.tasks)

    print(f"=== Sprint {sprint.number} Review ===")  # noqa: T201
    print(f"Period: {sprint.start_date} to {sprint.end_date}")  # noqa: T201
    print(f"Velocity: {done}/{total} tasks completed")  # noqa: T201
    print("\nGoals:")  # noqa: T201
    for g in sprint.goals:
        print(f"  - {g}")  # noqa: T201
    return 0


def _cmd_retro() -> int:
    retro_numbers = list_retros()
    if not retro_numbers:
        print("No retrospectives recorded yet.")  # noqa: T201
        return 0

    retro = load_retro(retro_numbers[-1])
    if retro is None:
        return 0

    print(f"=== Sprint {retro.sprint_number} Retrospective ===")  # noqa: T201
    print(f"Date: {retro.date}")  # noqa: T201
    print(f"Velocity: {retro.velocity} tasks")  # noqa: T201
    print(f"Token spend: ${retro.token_spend_total:.4f}")  # noqa: T201

    if retro.went_well:
        print("\nWent Well:")  # noqa: T201
        for item in retro.went_well:
            print(f"  + {item.text}")  # noqa: T201
    if retro.to_improve:
        print("\nTo Improve:")  # noqa: T201
        for item in retro.to_improve:
            print(f"  - {item.text}")  # noqa: T201
    if retro.action_items:
        print("\nAction Items:")  # noqa: T201
        for item in retro.action_items:
            print(f"  > [{item.priority}] {item.text}")  # noqa: T201
    return 0


def _cmd_roadmap() -> int:
    roadmap = load_roadmap()
    print(f"=== Company Roadmap (Sprint {roadmap.current_sprint}) ===")  # noqa: T201
    print(f"Last updated: {roadmap.last_updated}")  # noqa: T201
    print()  # noqa: T201

    for okr in roadmap.okrs:
        status_marker = "X" if okr.status != "active" else "O"
        print(f"[{status_marker}] {okr.id}: {okr.objective} ({okr.progress_pct:.0f}%)")  # noqa: T201
        for kr in okr.key_results:
            print(f"    - {kr}")  # noqa: T201
        print()  # noqa: T201
    return 0


def _cmd_init() -> int:
    sprint, roadmap = init_agile()
    print(f"Initialized Sprint {sprint.number}:")  # noqa: T201
    print(f"  Period: {sprint.start_date} to {sprint.end_date}")  # noqa: T201
    print(f"  Goals: {len(sprint.goals)}")  # noqa: T201
    print(f"  Tasks: {len(sprint.tasks)}")  # noqa: T201
    print(f"\nRoadmap created with {len(roadmap.okrs)} OKRs.")  # noqa: T201
    return 0


def _cmd_advance() -> int:
    new_sprint = advance_sprint()
    print(f"Advanced to Sprint {new_sprint.number}:")  # noqa: T201
    print(f"  Period: {new_sprint.start_date} to {new_sprint.end_date}")  # noqa: T201
    return 0


def _cmd_tasks() -> int:
    sprint = get_current_sprint()
    if sprint is None:
        print("No active sprint.")  # noqa: T201
        return 1

    print(f"=== Sprint {sprint.number} Tasks ===")  # noqa: T201
    if not sprint.tasks:
        print("  (no tasks)")  # noqa: T201
        return 0

    for task in sprint.tasks:
        marker = {"DONE": "X", "IN_PROGRESS": ">", "BLOCKED": "!", "TODO": " "}
        m = marker.get(task.status, " ")
        dept = task.assignee_department
        print(f"  [{m}] {task.id}: {task.title} ({dept}) [{task.priority}]")  # noqa: T201
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]

    match cmd:
        case "sprint":
            return _cmd_sprint()
        case "standup":
            return _cmd_standup()
        case "planning":
            return _cmd_planning()
        case "review":
            return _cmd_review()
        case "retro":
            return _cmd_retro()
        case "roadmap":
            return _cmd_roadmap()
        case "init":
            return _cmd_init()
        case "advance":
            return _cmd_advance()
        case "tasks":
            return _cmd_tasks()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
