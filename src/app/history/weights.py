from __future__ import annotations

from dataclasses import dataclass

from app.history.outcomes import TradeOutcome

FACTOR_NAMES = [
    "drawdown_depth",
    "vix_regime",
    "fed_regime",
    "yield_curve",
    "sec_sentiment",
]


@dataclass(frozen=True, slots=True)
class FactorWeight:
    """Weight for a single factor based on historical outcomes."""

    name: str
    favorable_wins: int
    favorable_total: int
    unfavorable_wins: int
    unfavorable_total: int
    weight: float


def calculate_weights(
    outcomes: list[TradeOutcome],
) -> list[FactorWeight]:
    """Calculate factor weights from completed trade outcomes.

    For each factor, compare win rate when favorable vs unfavorable.
    Higher differential = higher weight. Normalized to sum to 1.0.
    """
    completed = [o for o in outcomes if o.win is not None]
    if not completed:
        return []

    raw_scores: list[tuple[str, int, int, int, int, float]] = []

    for factor in FACTOR_NAMES:
        fav_wins = 0
        fav_total = 0
        unfav_wins = 0
        unfav_total = 0

        for outcome in completed:
            assessment = outcome.factors_at_entry.get(
                factor, "NEUTRAL",
            )
            if assessment == "FAVORABLE":
                fav_total += 1
                if outcome.win:
                    fav_wins += 1
            elif assessment == "UNFAVORABLE":
                unfav_total += 1
                if outcome.win:
                    unfav_wins += 1

        fav_rate = fav_wins / fav_total if fav_total > 0 else 0.5
        unfav_rate = (
            unfav_wins / unfav_total if unfav_total > 0 else 0.5
        )
        score = max(fav_rate - unfav_rate, 0.0)
        raw_scores.append(
            (factor, fav_wins, fav_total, unfav_wins, unfav_total, score),
        )

    total_score = sum(s[5] for s in raw_scores)

    if total_score == 0:
        equal_w = 1.0 / len(FACTOR_NAMES)
        return [
            FactorWeight(
                name=name,
                favorable_wins=fw,
                favorable_total=ft,
                unfavorable_wins=uw,
                unfavorable_total=ut,
                weight=equal_w,
            )
            for name, fw, ft, uw, ut, _score in raw_scores
        ]

    return [
        FactorWeight(
            name=name,
            favorable_wins=fw,
            favorable_total=ft,
            unfavorable_wins=uw,
            unfavorable_total=ut,
            weight=score / total_score,
        )
        for name, fw, ft, uw, ut, score in raw_scores
    ]


def format_learning_insights(
    weights: list[FactorWeight],
    total_trades: int,
    win_count: int,
    avg_pl_pct: float,
) -> str:
    """Format learning insights as a human-readable string."""
    if not weights:
        return "No completed trades yet — weights unavailable."

    lines = [f"Based on {total_trades} past trades:"]

    top = max(weights, key=lambda w: w.weight)
    lines.append(
        f"- Top factor: {top.name} (weight: {top.weight:.3f})",
    )

    win_rate = win_count / total_trades if total_trades > 0 else 0.0
    lines.append(
        f"- Win rate: {win_rate:.0%} | Avg P/L: {avg_pl_pct:+.1f}%",
    )

    return "\n".join(lines)
