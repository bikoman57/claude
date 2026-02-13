"""Tests for factor significance testing."""

from __future__ import annotations

from app.quant.significance import check_factor_significance


def test_significant_factor() -> None:
    """Clearly different distributions should be significant."""
    favorable = [0.10, 0.12, 0.08, 0.15, 0.11, 0.09, 0.13, 0.14]
    unfavorable = [-0.05, -0.03, -0.08, -0.02, -0.06, -0.04, -0.07, -0.01]
    result = check_factor_significance("test_factor", favorable, unfavorable)
    assert result.significant
    assert result.p_value < 0.05
    assert result.effect_size > 0
    assert result.sample_sizes == (8, 8)


def test_insignificant_factor() -> None:
    """Similar distributions should not be significant."""
    favorable = [0.05, 0.06, 0.04, 0.07, 0.03]
    unfavorable = [0.05, 0.04, 0.06, 0.03, 0.07]
    result = check_factor_significance("test_factor", favorable, unfavorable)
    assert not result.significant
    assert result.p_value > 0.05


def test_insufficient_data() -> None:
    """Too few samples returns not significant."""
    result = check_factor_significance("test_factor", [0.10], [0.05])
    assert not result.significant
    assert result.p_value == 1.0
    assert result.method == "insufficient_data"
