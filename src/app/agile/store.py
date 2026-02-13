"""Persistence layer for all agile artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.agile.models import (
    OKR,
    RetroItem,
    RetroRecord,
    Roadmap,
    Sprint,
    SprintStatus,
    SprintTask,
    StandupEntry,
    StandupRecord,
    TaskPriority,
    TaskStatus,
)

_AGILE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "agile"
_SPRINTS_PATH = _AGILE_DIR / "sprints.json"
_ROADMAP_PATH = _AGILE_DIR / "roadmap.json"
_STANDUPS_DIR = _AGILE_DIR / "standups"
_RETROS_DIR = _AGILE_DIR / "retros"


# ---------------------------------------------------------------------------
# Sprints
# ---------------------------------------------------------------------------


def load_sprints(path: Path | None = None) -> list[Sprint]:
    """Load all sprints."""
    store = path or _SPRINTS_PATH
    if not store.exists():
        return []
    raw: list[dict[str, object]] = json.loads(store.read_text(encoding="utf-8"))
    sprints: list[Sprint] = []
    for r in raw:
        tasks_raw: list[dict[str, object]] = r.pop("tasks", [])  # type: ignore[assignment]
        tasks = [SprintTask(**t) for t in tasks_raw]  # type: ignore[arg-type]
        sprints.append(Sprint(**r, tasks=tasks))  # type: ignore[arg-type]
    return sprints


def save_sprints(sprints: list[Sprint], path: Path | None = None) -> None:
    """Save all sprints."""
    store = path or _SPRINTS_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps([asdict(s) for s in sprints], indent=2),
        encoding="utf-8",
    )


def get_current_sprint(path: Path | None = None) -> Sprint | None:
    """Find the active sprint."""
    sprints = load_sprints(path)
    return next(
        (s for s in sprints if s.status == SprintStatus.ACTIVE),
        None,
    )


def _next_weekday(start: date, weekday: int) -> date:
    """Find the next occurrence of a weekday (0=Monday)."""
    days_ahead = weekday - start.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return start + timedelta(days=days_ahead)


def create_sprint(
    number: int,
    start: str,
    end: str,
    goals: list[str] | None = None,
) -> Sprint:
    """Create a new sprint."""
    return Sprint(
        number=number,
        start_date=start,
        end_date=end,
        goals=goals or [],
        status=SprintStatus.ACTIVE,
    )


def advance_sprint(path: Path | None = None) -> Sprint:
    """Close current sprint and create the next one."""
    sprints = load_sprints(path)
    current = next(
        (s for s in sprints if s.status == SprintStatus.ACTIVE),
        None,
    )

    if current:
        current.status = SprintStatus.COMPLETED
        current.velocity_points = sum(
            1 for t in current.tasks if t.status == TaskStatus.DONE
        )

    next_number = (current.number + 1) if current else 1
    today = datetime.now(tz=UTC).date()
    # Next sprint starts next Monday.
    next_monday = today if today.weekday() == 0 else _next_weekday(today, 0)
    next_friday = next_monday + timedelta(days=4)

    new_sprint = create_sprint(
        number=next_number,
        start=next_monday.isoformat(),
        end=next_friday.isoformat(),
    )
    sprints.append(new_sprint)
    save_sprints(sprints, path)
    return new_sprint


def is_sprint_over(sprint: Sprint | None) -> bool:
    """Check if the sprint's end date has passed."""
    if sprint is None:
        return True
    return date.fromisoformat(sprint.end_date) < datetime.now(tz=UTC).date()


# ---------------------------------------------------------------------------
# Standups
# ---------------------------------------------------------------------------


def save_standup(
    record: StandupRecord,
    path: Path | None = None,
) -> Path:
    """Save a daily standup record."""
    base = path or _STANDUPS_DIR
    base.mkdir(parents=True, exist_ok=True)
    file = base / f"{record.date}.json"
    file.write_text(
        json.dumps(asdict(record), indent=2),
        encoding="utf-8",
    )
    return file


def load_standup(
    date_str: str,
    path: Path | None = None,
) -> StandupRecord | None:
    """Load a standup record for a specific date."""
    base = path or _STANDUPS_DIR
    file = base / f"{date_str}.json"
    if not file.exists():
        return None
    raw = json.loads(file.read_text(encoding="utf-8"))
    entries = [StandupEntry(**e) for e in raw.pop("entries", [])]
    return StandupRecord(**raw, entries=entries)


def list_standups(path: Path | None = None) -> list[str]:
    """List all standup dates."""
    base = path or _STANDUPS_DIR
    if not base.exists():
        return []
    return sorted(f.stem for f in base.glob("*.json"))


# ---------------------------------------------------------------------------
# Retrospectives
# ---------------------------------------------------------------------------


def save_retro(
    record: RetroRecord,
    path: Path | None = None,
) -> Path:
    """Save a sprint retrospective record."""
    base = path or _RETROS_DIR
    base.mkdir(parents=True, exist_ok=True)
    file = base / f"sprint-{record.sprint_number}.json"
    file.write_text(
        json.dumps(asdict(record), indent=2),
        encoding="utf-8",
    )
    return file


def load_retro(
    sprint_number: int,
    path: Path | None = None,
) -> RetroRecord | None:
    """Load a retrospective for a specific sprint."""
    base = path or _RETROS_DIR
    file = base / f"sprint-{sprint_number}.json"
    if not file.exists():
        return None
    raw = json.loads(file.read_text(encoding="utf-8"))
    went_well = [RetroItem(**i) for i in raw.pop("went_well", [])]
    to_improve = [RetroItem(**i) for i in raw.pop("to_improve", [])]
    action_items = [RetroItem(**i) for i in raw.pop("action_items", [])]
    return RetroRecord(
        **raw,
        went_well=went_well,
        to_improve=to_improve,
        action_items=action_items,
    )


def list_retros(path: Path | None = None) -> list[int]:
    """List all retrospective sprint numbers."""
    base = path or _RETROS_DIR
    if not base.exists():
        return []
    return sorted(
        int(f.stem.removeprefix("sprint-")) for f in base.glob("sprint-*.json")
    )


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------


def load_roadmap(path: Path | None = None) -> Roadmap:
    """Load the company roadmap."""
    store = path or _ROADMAP_PATH
    if not store.exists():
        return default_roadmap()
    raw = json.loads(store.read_text(encoding="utf-8"))
    okrs = [OKR(**o) for o in raw.pop("okrs", [])]
    return Roadmap(**raw, okrs=okrs)


def save_roadmap(roadmap: Roadmap, path: Path | None = None) -> None:
    """Save the company roadmap."""
    store = path or _ROADMAP_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(asdict(roadmap), indent=2),
        encoding="utf-8",
    )


def default_roadmap() -> Roadmap:
    """Create default company roadmap with initial OKRs."""
    return Roadmap(
        okrs=[
            OKR(
                id="OKR-1",
                objective="Achieve consistent trading signal accuracy",
                key_results=[
                    "Signal accuracy >60% over 30 days",
                    "All 12 confidence factors contributing to predictions",
                    "Factor weight learning from >10 completed trades",
                ],
            ),
            OKR(
                id="OKR-2",
                objective="Optimize operational costs",
                key_results=[
                    "Weekly token spend under budget for all departments",
                    "Pipeline success rate >95%",
                    "All modules running under 60s average",
                ],
            ),
            OKR(
                id="OKR-3",
                objective="Maximize intelligence gathering value",
                key_results=[
                    "Correlate intelligence factors with trade outcomes",
                    "Congress trading signal accuracy >50%",
                    "Geopolitical risk properly reflected in sector signals",
                ],
            ),
        ],
        current_sprint=1,
        last_updated=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_agile(path: Path | None = None) -> tuple[Sprint, Roadmap]:
    """Initialize Sprint 1 and the default roadmap."""
    today = datetime.now(tz=UTC).date()
    # Start sprint on current Monday (or today if Monday).
    monday = today if today.weekday() == 0 else today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    sprint = Sprint(
        number=1,
        start_date=monday.isoformat(),
        end_date=friday.isoformat(),
        goals=[
            "Establish baseline pipeline reliability metrics",
            "Track token costs for one full week",
            "Complete first sprint cycle with all ceremonies",
        ],
        tasks=[
            SprintTask(
                id="S1-T1",
                title="Verify all pipeline modules run successfully",
                description="Run full pipeline and document any failures",
                assignee_department="operations",
                priority=TaskPriority.HIGH,
                created_date=today.isoformat(),
            ),
            SprintTask(
                id="S1-T2",
                title="Establish token cost baseline",
                description="Record token usage for 5 trading days",
                assignee_department="operations",
                priority=TaskPriority.HIGH,
                created_date=today.isoformat(),
            ),
            SprintTask(
                id="S1-T3",
                title="Review signal accuracy for tracked ETFs",
                description="Compare signals against actual price movements",
                assignee_department="trading",
                priority=TaskPriority.MEDIUM,
                created_date=today.isoformat(),
            ),
        ],
        status=SprintStatus.ACTIVE,
    )

    sprints_path = (path or _AGILE_DIR) / "sprints.json" if path else None
    save_sprints([sprint], sprints_path)

    roadmap = default_roadmap()
    roadmap_path = (path or _AGILE_DIR) / "roadmap.json" if path else None
    save_roadmap(roadmap, roadmap_path)

    return sprint, roadmap
