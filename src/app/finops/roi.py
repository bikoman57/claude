"""Department ROI calculations linking token spend to trading outcomes."""

from __future__ import annotations

from app.finops.models import DepartmentROI
from app.finops.tracker import AGENT_DEPARTMENT_MAP, summarize_period
from app.history.outcomes import get_completed_outcomes


def calculate_department_roi(
    department: str,
    period_start: str,
    period_end: str,
) -> DepartmentROI:
    """Calculate ROI for a department over a period."""
    summary = summarize_period(period_start, period_end)
    token_cost = summary.by_department.get(department, 0.0)

    # Trading P/L from completed outcomes in the period.
    outcomes = get_completed_outcomes()
    period_outcomes = [
        o
        for o in outcomes
        if o.exit_date and period_start <= o.exit_date <= period_end + "Z"
    ]
    trading_pl = sum(o.pl_pct or 0.0 for o in period_outcomes) * 100

    # Signal accuracy: wins / total.
    total = len(period_outcomes)
    wins = sum(1 for o in period_outcomes if o.win)
    accuracy = (wins / total * 100) if total > 0 else 0.0

    # Pipeline success rate: based on department's agents.
    dept_agents = [a for a, d in AGENT_DEPARTMENT_MAP.items() if d == department]
    pipeline_rate = 100.0 if dept_agents else 0.0

    roi_ratio = (trading_pl / token_cost) if token_cost > 0 else 0.0

    return DepartmentROI(
        department=department,
        period=f"{period_start}_to_{period_end}",
        token_cost_usd=round(token_cost, 4),
        trading_pl_usd=round(trading_pl, 4),
        signal_accuracy_pct=round(accuracy, 1),
        pipeline_success_rate=round(pipeline_rate, 1),
        roi_ratio=round(roi_ratio, 2),
    )


def calculate_all_roi(
    period_start: str,
    period_end: str,
) -> list[DepartmentROI]:
    """Calculate ROI for all departments."""
    departments = sorted(set(AGENT_DEPARTMENT_MAP.values()))
    return [
        calculate_department_roi(dept, period_start, period_end) for dept in departments
    ]
