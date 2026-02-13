"""FinOps data models for token tracking, budgets, and ROI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ModelTier(StrEnum):
    """Claude model pricing tiers."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


# Cost per 1M tokens (input_rate, output_rate) in USD.
MODEL_COSTS: dict[ModelTier, tuple[float, float]] = {
    ModelTier.OPUS: (15.0, 75.0),
    ModelTier.SONNET: (3.0, 15.0),
    ModelTier.HAIKU: (0.25, 1.25),
}


@dataclass(frozen=True, slots=True)
class TokenUsageRecord:
    """One agent invocation's token usage."""

    timestamp: str
    session: str  # "pre-market", "post-market", "manual"
    agent_name: str
    department: str
    model_tier: str  # ModelTier value
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    run_id: str  # e.g. "2026-02-12_pre-market"


@dataclass
class DailyTokenSummary:
    """Aggregated token usage for one day."""

    date: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    by_department: dict[str, float] = field(default_factory=dict)
    by_agent: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)
    record_count: int = 0


@dataclass(frozen=True, slots=True)
class DepartmentBudget:
    """Budget allocation for one department."""

    department: str
    weekly_budget_usd: float
    monthly_budget_usd: float
    priority: str = "normal"  # "critical", "normal", "low"


@dataclass
class BudgetConfig:
    """All department budgets."""

    budgets: list[DepartmentBudget] = field(default_factory=list)
    total_weekly_usd: float = 0.0
    total_monthly_usd: float = 0.0
    last_updated: str = ""


@dataclass
class DepartmentROI:
    """ROI tracking for one department over a period."""

    department: str
    period: str  # "sprint-3", "2026-W07"
    token_cost_usd: float
    trading_pl_usd: float
    signal_accuracy_pct: float
    pipeline_success_rate: float
    roi_ratio: float  # trading_pl / token_cost
