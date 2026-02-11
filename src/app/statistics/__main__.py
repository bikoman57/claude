from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.statistics.breadth import analyze_market_breadth
from app.statistics.correlations import (
    calculate_correlations,
    fetch_risk_indicators,
)
from app.statistics.sectors import analyze_sector_rotation

USAGE = """\
Usage:
  uv run python -m app.statistics sectors       Sector rotation analysis
  uv run python -m app.statistics breadth       Market breadth indicators
  uv run python -m app.statistics risk          Risk indicators (gold, oil, DXY)
  uv run python -m app.statistics correlations  Cross-asset correlations
  uv run python -m app.statistics dashboard     Full statistics dashboard
"""


def cmd_sectors() -> int:
    """Print sector rotation analysis."""
    rotation = analyze_sector_rotation()
    output = {
        "rotation_signal": rotation.rotation_signal,
        "leaders": [asdict(s) for s in rotation.leaders],
        "laggards": [asdict(s) for s in rotation.laggards],
        "as_of": rotation.as_of,
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_breadth() -> int:
    """Print market breadth indicators."""
    breadth = analyze_market_breadth()
    print(json.dumps(asdict(breadth), indent=2))  # noqa: T201
    return 0


def cmd_risk() -> int:
    """Print risk indicators."""
    risk = fetch_risk_indicators()
    print(json.dumps(asdict(risk), indent=2))  # noqa: T201
    return 0


def cmd_correlations() -> int:
    """Print cross-asset correlations."""
    corr = calculate_correlations()
    if corr is None:
        print(json.dumps({"error": "insufficient data"}))  # noqa: T201
        return 0
    print(json.dumps(asdict(corr), indent=2))  # noqa: T201
    return 0


def cmd_dashboard() -> int:
    """Print full statistics dashboard."""
    risk = fetch_risk_indicators()
    corr = calculate_correlations()

    output: dict[str, object] = {
        "risk_indicators": asdict(risk),
        "correlations": asdict(corr) if corr else None,
        "overall_assessment": risk.risk_assessment,
        "as_of": risk.as_of,
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    match command:
        case "sectors":
            exit_code = cmd_sectors()
        case "breadth":
            exit_code = cmd_breadth()
        case "risk":
            exit_code = cmd_risk()
        case "correlations":
            exit_code = cmd_correlations()
        case "dashboard":
            exit_code = cmd_dashboard()
        case _:
            print(  # noqa: T201
                f"Unknown command: {command}",
                file=sys.stderr,
            )
            print(USAGE, file=sys.stderr)  # noqa: T201
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
