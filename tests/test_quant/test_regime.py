"""Tests for market regime detection."""

from __future__ import annotations

from app.quant.regime import Regime, detect_regime


def test_bull_regime() -> None:
    """Rising prices with low vol detected as BULL."""
    # Steadily rising prices
    closes = [100.0 + i * 0.2 for i in range(100)]
    result = detect_regime(closes)
    assert result.regime == Regime.BULL
    assert result.confidence_pct > 0
    assert result.return_60d > 0


def test_bear_regime() -> None:
    """Falling prices detected as BEAR."""
    closes = [100.0 - i * 0.3 for i in range(100)]
    result = detect_regime(closes)
    assert result.regime == Regime.BEAR
    assert result.return_60d < 0


def test_range_regime() -> None:
    """Flat prices detected as RANGE."""
    import math

    closes = [100.0 + math.sin(i / 5) * 2 for i in range(100)]
    result = detect_regime(closes)
    assert result.regime == Regime.RANGE


def test_insufficient_data() -> None:
    """Short series returns RANGE with 0 confidence."""
    result = detect_regime([100.0, 101.0, 99.0])
    assert result.regime == Regime.RANGE
    assert result.confidence_pct == 0.0
    assert result.method == "insufficient_data"
