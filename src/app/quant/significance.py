"""Factor significance testing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SignificanceResult:
    """Result of a factor significance test."""

    factor_name: str
    favorable_mean: float
    unfavorable_mean: float
    effect_size: float
    p_value: float
    significant: bool
    sample_sizes: tuple[int, int]
    method: str


def check_factor_significance(
    factor_name: str,
    favorable_returns: list[float],
    unfavorable_returns: list[float],
    alpha: float = 0.05,
) -> SignificanceResult:
    """Test whether a factor meaningfully separates trade outcomes.

    Uses a permutation test (bootstrap) since sample sizes are small.
    """
    if len(favorable_returns) < 2 or len(unfavorable_returns) < 2:
        return SignificanceResult(
            factor_name=factor_name,
            favorable_mean=0.0,
            unfavorable_mean=0.0,
            effect_size=0.0,
            p_value=1.0,
            significant=False,
            sample_sizes=(len(favorable_returns), len(unfavorable_returns)),
            method="insufficient_data",
        )

    fav = np.array(favorable_returns)
    unfav = np.array(unfavorable_returns)

    observed_diff = float(np.mean(fav) - np.mean(unfav))

    # Permutation test
    combined = np.concatenate([fav, unfav])
    n_fav = len(fav)
    rng = np.random.default_rng(42)
    n_permutations = 1000
    perm_diffs = np.empty(n_permutations)

    for i in range(n_permutations):
        perm = rng.permutation(combined)
        perm_diffs[i] = np.mean(perm[:n_fav]) - np.mean(perm[n_fav:])

    p_value = float(np.mean(np.abs(perm_diffs) >= np.abs(observed_diff)))

    # Effect size (Cohen's d)
    pooled_std = float(np.sqrt((np.var(fav) + np.var(unfav)) / 2))
    effect_size = observed_diff / pooled_std if pooled_std > 0 else 0.0

    return SignificanceResult(
        factor_name=factor_name,
        favorable_mean=round(float(np.mean(fav)), 4),
        unfavorable_mean=round(float(np.mean(unfav)), 4),
        effect_size=round(effect_size, 3),
        p_value=round(p_value, 4),
        significant=p_value < alpha,
        sample_sizes=(len(favorable_returns), len(unfavorable_returns)),
        method="permutation_test",
    )
