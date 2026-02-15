"""Agile data models: sprints, tasks, ceremonies, roadmap."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SprintStatus(StrEnum):
    """Sprint lifecycle states."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskStatus(StrEnum):
    """Sprint task states."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class TaskPriority(StrEnum):
    """Task priority levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CeremonyType(StrEnum):
    """Types of Agile ceremonies."""

    STANDUP = "STANDUP"
    PLANNING = "PLANNING"
    REVIEW = "REVIEW"
    RETROSPECTIVE = "RETROSPECTIVE"


@dataclass
class SprintTask:
    """A task within a sprint."""

    id: str  # e.g., "S3-T1"
    title: str
    description: str
    assignee_department: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.TODO
    created_date: str = ""
    completed_date: str | None = None
    notes: str = ""


@dataclass
class Sprint:
    """A one-week sprint (Monday through Sunday)."""

    number: int
    start_date: str  # ISO date YYYY-MM-DD
    end_date: str  # ISO date YYYY-MM-DD
    goals: list[str] = field(default_factory=list)
    tasks: list[SprintTask] = field(default_factory=list)
    status: SprintStatus = SprintStatus.PLANNED
    velocity_points: int = 0
    notes: str = ""


@dataclass(frozen=True, slots=True)
class StandupEntry:
    """One department's standup contribution."""

    department: str
    agent: str
    yesterday: str
    today: str
    blockers: str


@dataclass
class StandupRecord:
    """A daily standup ceremony record."""

    date: str
    sprint_number: int
    session: str  # "pre-market" or "post-market"
    entries: list[StandupEntry] = field(default_factory=list)
    summary: str = ""
    generated_at: str = ""


@dataclass
class RetroItem:
    """A retrospective item."""

    category: str  # "went_well", "improve", "action_item"
    text: str
    department: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM


@dataclass
class RetroRecord:
    """A sprint retrospective ceremony record."""

    sprint_number: int
    date: str
    went_well: list[RetroItem] = field(default_factory=list)
    to_improve: list[RetroItem] = field(default_factory=list)
    action_items: list[RetroItem] = field(default_factory=list)
    velocity: int = 0
    token_spend_total: float = 0.0
    trading_outcomes: str = ""
    generated_at: str = ""


@dataclass
class OKR:
    """An Objective and Key Result for the roadmap."""

    id: str
    objective: str
    key_results: list[str] = field(default_factory=list)
    progress_pct: float = 0.0
    target_sprint: int | None = None
    status: str = "active"


@dataclass
class Roadmap:
    """Company roadmap with OKRs."""

    okrs: list[OKR] = field(default_factory=list)
    current_sprint: int = 1
    last_updated: str = ""
