"""DevOps data models for pipeline health and system monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ModuleHealth:
    """Health status of one data pipeline module."""

    name: str
    success_rate_7d: float
    avg_duration_seconds: float
    trend: str  # "improving", "stable", "degrading"
    last_failure: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class SystemHealthScore:
    """Overall system health score."""

    score: float  # 0.0 - 1.0
    grade: str  # "A", "B", "C", "D", "F"
    pipeline_health: float
    data_freshness: float
    module_count: int
    details: tuple[str, ...] = ()


@dataclass
class PipelineHistory:
    """Historical pipeline run data for trend analysis."""

    date: str
    session: str
    modules_ok: int
    modules_total: int
    duration_seconds: float
    module_results: dict[str, bool] = field(default_factory=dict)
