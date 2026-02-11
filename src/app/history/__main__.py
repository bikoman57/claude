from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.history.outcomes import get_completed_outcomes, load_outcomes
from app.history.recorder import list_snapshots, load_snapshot
from app.history.weights import calculate_weights, format_learning_insights

USAGE = """\
Usage:
  uv run python -m app.history outcomes     List all trade outcomes
  uv run python -m app.history weights      Show factor weights
  uv run python -m app.history summary      Summary of learning
  uv run python -m app.history snapshots    List recent snapshots
"""


def cmd_outcomes() -> int:
    """List all trade outcomes."""
    outcomes = load_outcomes()
    if not outcomes:
        print("No trade outcomes recorded yet.")  # noqa: T201
        return 0
    print(  # noqa: T201
        json.dumps([asdict(o) for o in outcomes], indent=2),
    )
    return 0


def cmd_weights() -> int:
    """Show factor weights from completed trades."""
    completed = get_completed_outcomes()
    if not completed:
        print(  # noqa: T201
            "No completed trades yet. Weights need at least one closed trade.",
        )
        return 0
    weights = calculate_weights(completed)
    for w in weights:
        print(  # noqa: T201
            f"  {w.name:<20} weight={w.weight:.3f}"
            f" (fav: {w.favorable_wins}/{w.favorable_total},"
            f" unfav: {w.unfavorable_wins}/{w.unfavorable_total})",
        )
    return 0


def cmd_summary() -> int:
    """Overall learning summary."""
    completed = get_completed_outcomes()
    all_outcomes = load_outcomes()
    open_trades = [o for o in all_outcomes if o.exit_date is None]

    print(f"Completed trades: {len(completed)}")  # noqa: T201
    print(f"Open trades: {len(open_trades)}")  # noqa: T201

    if completed:
        wins = sum(1 for o in completed if o.win)
        pls = [o.pl_pct for o in completed if o.pl_pct is not None]
        avg_pl = sum(pls) / len(pls) * 100 if pls else 0.0
        weights = calculate_weights(completed)
        insights = format_learning_insights(
            weights,
            len(completed),
            wins,
            avg_pl,
        )
        print(insights)  # noqa: T201
    else:
        print(  # noqa: T201
            "No completed trades yet — weights unavailable.",
        )

    snapshots = list_snapshots()
    print(f"Analysis snapshots: {len(snapshots)}")  # noqa: T201
    return 0


def cmd_snapshots() -> int:
    """List recent analysis snapshots."""
    snapshots = list_snapshots()
    if not snapshots:
        print("No analysis snapshots saved yet.")  # noqa: T201
        return 0
    for path in snapshots[:10]:
        snap = load_snapshot(path)
        print(f"  {snap.timestamp}: {snap.summary}")  # noqa: T201
    if len(snapshots) > 10:
        print(  # noqa: T201
            f"  ... and {len(snapshots) - 10} more",
        )
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]

    match command:
        case "outcomes":
            exit_code = cmd_outcomes()
        case "weights":
            exit_code = cmd_weights()
        case "summary":
            exit_code = cmd_summary()
        case "snapshots":
            exit_code = cmd_snapshots()
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
