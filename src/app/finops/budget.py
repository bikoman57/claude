"""Budget management and reallocation suggestions."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.finops.models import BudgetConfig, DepartmentBudget, DepartmentROI
from app.finops.tracker import summarize_period

_BUDGET_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "finops"
    / "budgets.json"
)

DEFAULT_BUDGETS: list[DepartmentBudget] = [
    DepartmentBudget(
        "executive",
        25.0,
        100.0,
        priority="critical",
    ),
    DepartmentBudget(
        "trading",
        15.0,
        60.0,
        priority="critical",
    ),
    DepartmentBudget(
        "research",
        30.0,
        120.0,
        priority="normal",
    ),
    DepartmentBudget(
        "intelligence",
        15.0,
        60.0,
        priority="normal",
    ),
    DepartmentBudget(
        "risk",
        10.0,
        40.0,
        priority="critical",
    ),
    DepartmentBudget(
        "operations", weekly_budget_usd=5.0, monthly_budget_usd=20.0, priority="low"
    ),
]


def load_budgets(path: Path | None = None) -> BudgetConfig:
    """Load budget configuration."""
    store = path or _BUDGET_PATH
    if not store.exists():
        return _default_config()
    raw = json.loads(store.read_text(encoding="utf-8"))
    budgets = [DepartmentBudget(**b) for b in raw.get("budgets", [])]
    return BudgetConfig(
        budgets=budgets,
        total_weekly_usd=raw.get("total_weekly_usd", 0.0),
        total_monthly_usd=raw.get("total_monthly_usd", 0.0),
        last_updated=raw.get("last_updated", ""),
    )


def save_budgets(config: BudgetConfig, path: Path | None = None) -> None:
    """Save budget configuration."""
    store = path or _BUDGET_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "budgets": [asdict(b) for b in config.budgets],
        "total_weekly_usd": config.total_weekly_usd,
        "total_monthly_usd": config.total_monthly_usd,
        "last_updated": config.last_updated,
    }
    store.write_text(json.dumps(data, indent=2), encoding="utf-8")


def init_budgets(path: Path | None = None) -> BudgetConfig:
    """Initialize default budget configuration."""
    config = _default_config()
    save_budgets(config, path)
    return config


def check_budget_status(
    department: str,
    *,
    path: Path | None = None,
) -> dict[str, object]:
    """Check current spend vs budget for a department.

    Returns dict with: spent, budget, remaining, pct_used, alert.
    """
    config = load_budgets(path)
    budget = next((b for b in config.budgets if b.department == department), None)
    if budget is None:
        return {"error": f"Unknown department: {department}"}

    today = datetime.now(tz=UTC).date()
    week_start = today - timedelta(days=today.weekday())
    summary = summarize_period(
        week_start.isoformat(),
        today.isoformat(),
        path=path,
    )
    spent = summary.by_department.get(department, 0.0)
    remaining = budget.weekly_budget_usd - spent
    pct_used = (
        (spent / budget.weekly_budget_usd * 100)
        if budget.weekly_budget_usd > 0
        else 0.0
    )

    alert = "OK"
    if pct_used >= 100:
        alert = "OVER_BUDGET"
    elif pct_used >= 80:
        alert = "WARNING"

    return {
        "department": department,
        "spent_usd": round(spent, 4),
        "weekly_budget_usd": budget.weekly_budget_usd,
        "remaining_usd": round(remaining, 4),
        "pct_used": round(pct_used, 1),
        "alert": alert,
        "priority": budget.priority,
    }


def suggest_reallocation(
    roi_data: list[DepartmentROI],
) -> list[str]:
    """Suggest budget reallocations based on ROI."""
    suggestions: list[str] = []
    if not roi_data:
        return ["No ROI data available for reallocation suggestions."]

    sorted_roi = sorted(roi_data, key=lambda r: r.roi_ratio, reverse=True)
    top = sorted_roi[0]
    bottom = sorted_roi[-1]

    if top.roi_ratio > 0 and bottom.roi_ratio <= 0:
        suggestions.append(
            f"Increase {top.department} budget (ROI: {top.roi_ratio:.1f}x), "
            f"decrease {bottom.department} (ROI: {bottom.roi_ratio:.1f}x)"
        )

    for dept_roi in sorted_roi:
        if dept_roi.token_cost_usd > 0 and dept_roi.roi_ratio < -1.0:
            suggestions.append(
                f"Review {dept_roi.department}:"
                f" spending ${dept_roi.token_cost_usd:.2f}"
                f" with negative ROI ({dept_roi.roi_ratio:.1f}x)"
            )

    if not suggestions:
        suggestions.append("All departments within acceptable ROI range.")

    return suggestions


def _default_config() -> BudgetConfig:
    """Create default budget configuration."""
    total_weekly = sum(b.weekly_budget_usd for b in DEFAULT_BUDGETS)
    total_monthly = sum(b.monthly_budget_usd for b in DEFAULT_BUDGETS)
    return BudgetConfig(
        budgets=list(DEFAULT_BUDGETS),
        total_weekly_usd=total_weekly,
        total_monthly_usd=total_monthly,
        last_updated=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
