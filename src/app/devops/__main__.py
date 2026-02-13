"""DevOps CLI.

Usage:
    python -m app.devops health        System health score
    python -m app.devops pipeline      Pipeline module health
    python -m app.devops trends        Duration and success trends
"""

from __future__ import annotations

import sys

from app.devops.health import (
    get_all_module_health,
    get_system_health,
    load_pipeline_history,
)


def _cmd_health() -> int:
    health = get_system_health()
    print(f"=== System Health: {health.grade} ({health.score:.0%}) ===")  # noqa: T201
    print(f"Pipeline health:  {health.pipeline_health:.0%}")  # noqa: T201
    print(f"Data freshness:   {health.data_freshness:.0%}")  # noqa: T201
    print(f"Tracked modules:  {health.module_count}")  # noqa: T201
    if health.details:
        print("\nIssues:")  # noqa: T201
        for d in health.details:
            print(f"  - {d}")  # noqa: T201
    return 0


def _cmd_pipeline() -> int:
    modules = get_all_module_health()
    if not modules:
        print("No pipeline history available.")  # noqa: T201
        return 0

    print("=== Pipeline Module Health (7-day) ===")  # noqa: T201
    for m in modules:
        trend_marker = {
            "improving": "+",
            "degrading": "-",
            "stable": "=",
            "unknown": "?",
        }
        marker = trend_marker.get(m.trend, "?")
        failure_info = f" (last fail: {m.last_failure})" if m.last_failure else ""
        print(  # noqa: T201
            f"  [{marker}] {m.name:<25} {m.success_rate_7d:>5.1f}%{failure_info}"
        )
    return 0


def _cmd_trends() -> int:
    history = load_pipeline_history(days=14)
    if not history:
        print("No pipeline history available.")  # noqa: T201
        return 0

    print("=== Pipeline Trends (14-day) ===")  # noqa: T201
    for h in history[-10:]:
        rate = h.modules_ok / h.modules_total * 100 if h.modules_total > 0 else 0
        bar = "#" * int(rate / 5)
        print(  # noqa: T201
            f"  {h.date} {h.session:<12} {h.modules_ok:>2}/{h.modules_total:<2} "
            f"({rate:>5.1f}%) {bar}"
        )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]

    match cmd:
        case "health":
            return _cmd_health()
        case "pipeline":
            return _cmd_pipeline()
        case "trends":
            return _cmd_trends()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
