"""FinOps CLI.

Usage:
    python -m app.finops dashboard        Token usage dashboard
    python -m app.finops today            Today's token usage
    python -m app.finops budget           Show budgets vs actuals
    python -m app.finops allocate         Suggest budget reallocation
    python -m app.finops roi              Department ROI report
    python -m app.finops agent <name>     Token usage for specific agent
    python -m app.finops init             Initialize default budgets
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

from app.finops.budget import (
    check_budget_status,
    init_budgets,
    load_budgets,
    suggest_reallocation,
)
from app.finops.roi import calculate_all_roi
from app.finops.tracker import (
    AGENT_DEPARTMENT_MAP,
    load_usage,
    summarize_day,
    summarize_period,
)


def _cmd_dashboard() -> int:
    today = datetime.now(tz=UTC).date()
    week_start = today - timedelta(days=today.weekday())

    print("=== FinOps Token Usage Dashboard ===")  # noqa: T201
    print(f"Week: {week_start.isoformat()} to {today.isoformat()}")  # noqa: T201
    print()  # noqa: T201

    summary = summarize_period(week_start.isoformat(), today.isoformat())
    print(f"Total input tokens:  {summary.total_input_tokens:,}")  # noqa: T201
    print(f"Total output tokens: {summary.total_output_tokens:,}")  # noqa: T201
    print(f"Total cost:          ${summary.total_cost_usd:.4f}")  # noqa: T201
    print(f"Records:             {summary.record_count}")  # noqa: T201
    print()  # noqa: T201

    if summary.by_department:
        print("By Department:")  # noqa: T201
        for dept, cost in sorted(summary.by_department.items(), key=lambda x: -x[1]):
            print(f"  {dept:<15} ${cost:.4f}")  # noqa: T201
        print()  # noqa: T201

    if summary.by_model:
        print("By Model:")  # noqa: T201
        for model, cost in sorted(summary.by_model.items(), key=lambda x: -x[1]):
            print(f"  {model:<10} ${cost:.4f}")  # noqa: T201

    return 0


def _cmd_today() -> int:
    today_str = datetime.now(tz=UTC).date().isoformat()
    summary = summarize_day(today_str)

    print(f"=== Token Usage for {today_str} ===")  # noqa: T201
    print(f"Total cost: ${summary.total_cost_usd:.4f}")  # noqa: T201
    print(  # noqa: T201
        f"Input: {summary.total_input_tokens:,}"
        f" | Output: {summary.total_output_tokens:,}"
    )
    print(f"Records: {summary.record_count}")  # noqa: T201

    if summary.by_agent:
        print()  # noqa: T201
        print("By Agent:")  # noqa: T201
        for agent, cost in sorted(summary.by_agent.items(), key=lambda x: -x[1]):
            print(f"  {agent:<35} ${cost:.4f}")  # noqa: T201

    return 0


def _cmd_budget() -> int:
    config = load_budgets()
    if not config.budgets:
        print("No budgets configured. Run: python -m app.finops init")  # noqa: T201
        return 1

    print("=== Department Budgets ===")  # noqa: T201
    print(f"Total weekly:  ${config.total_weekly_usd:.2f}")  # noqa: T201
    print(f"Total monthly: ${config.total_monthly_usd:.2f}")  # noqa: T201
    print()  # noqa: T201

    for budget in config.budgets:
        status = check_budget_status(budget.department)
        alert = status.get("alert", "?")
        spent = status.get("spent_usd", 0.0)
        pct = status.get("pct_used", 0.0)
        marker = (
            " !!!" if alert == "OVER_BUDGET" else (" !" if alert == "WARNING" else "")
        )
        print(  # noqa: T201
            f"  {budget.department:<15} "
            f"${spent:>7.2f} / ${budget.weekly_budget_usd:>6.2f}  "
            f"({pct:>5.1f}%) [{budget.priority}]{marker}"
        )

    return 0


def _cmd_allocate() -> int:
    today = datetime.now(tz=UTC).date()
    week_start = today - timedelta(days=today.weekday())

    roi_data = calculate_all_roi(week_start.isoformat(), today.isoformat())
    suggestions = suggest_reallocation(roi_data)

    print("=== Budget Reallocation Suggestions ===")  # noqa: T201
    for s in suggestions:
        print(f"  - {s}")  # noqa: T201

    return 0


def _cmd_roi() -> int:
    today = datetime.now(tz=UTC).date()
    week_start = today - timedelta(days=today.weekday())

    roi_data = calculate_all_roi(week_start.isoformat(), today.isoformat())

    print("=== Department ROI Report ===")  # noqa: T201
    print(f"Period: {week_start.isoformat()} to {today.isoformat()}")  # noqa: T201
    print()  # noqa: T201

    for roi in sorted(roi_data, key=lambda r: -r.roi_ratio):
        cost = roi.token_cost_usd
        ratio = roi.roi_ratio
        print(  # noqa: T201
            f"  {roi.department:<15}"
            f" cost=${cost:>7.4f}  ROI={ratio:>6.1f}x"
        )

    return 0


def _cmd_agent(name: str) -> int:
    records = load_usage()
    agent_records = [r for r in records if r.agent_name == name]

    if not agent_records:
        print(f"No records found for agent: {name}")  # noqa: T201
        return 0

    dept = AGENT_DEPARTMENT_MAP.get(name, "unknown")
    total_cost = sum(r.cost_usd for r in agent_records)
    total_input = sum(r.input_tokens for r in agent_records)
    total_output = sum(r.output_tokens for r in agent_records)

    print(f"=== Agent: {name} ({dept}) ===")  # noqa: T201
    print(f"Total invocations: {len(agent_records)}")  # noqa: T201
    print(f"Total cost:        ${total_cost:.4f}")  # noqa: T201
    print(f"Total input:       {total_input:,} tokens")  # noqa: T201
    print(f"Total output:      {total_output:,} tokens")  # noqa: T201

    if agent_records:
        last = agent_records[-1]
        print(f"Last run:          {last.timestamp} ({last.session})")  # noqa: T201

    return 0


def _cmd_init() -> int:
    config = init_budgets()
    print("Default budgets initialized:")  # noqa: T201
    for b in config.budgets:
        print(f"  {b.department:<15} ${b.weekly_budget_usd:.2f}/week  [{b.priority}]")  # noqa: T201
    weekly = config.total_weekly_usd
    monthly = config.total_monthly_usd
    print(  # noqa: T201
        f"\nTotal: ${weekly:.2f}/week, ${monthly:.2f}/month"
    )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]

    match cmd:
        case "dashboard":
            return _cmd_dashboard()
        case "today":
            return _cmd_today()
        case "budget":
            return _cmd_budget()
        case "allocate":
            return _cmd_allocate()
        case "roi":
            return _cmd_roi()
        case "agent":
            if len(sys.argv) < 3:
                print("Usage: python -m app.finops agent <name>")  # noqa: T201
                return 1
            return _cmd_agent(sys.argv[2])
        case "init":
            return _cmd_init()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
