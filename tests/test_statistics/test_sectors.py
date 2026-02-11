from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.statistics.sectors import (
    SectorStrength,
    analyze_sector_rotation,
    calculate_sector_strength,
)


def _mock_history(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": prices, "Volume": [1000] * len(prices)},
    )


@patch("app.statistics.sectors.yf.Ticker")
def test_calculate_sector_strength(mock_ticker_cls):
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(
        [100.0, 102.0, 104.0, 106.0, 108.0, 110.0],
    )
    mock_ticker_cls.return_value = mock_t

    s = calculate_sector_strength("XLK", "Technology", 0.05)
    assert s is not None
    assert s.ticker == "XLK"
    assert s.price == 110.0
    assert s.change_20d_pct > 0


@patch("app.statistics.sectors.yf.Ticker")
def test_calculate_sector_strength_insufficient(mock_ticker_cls):
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history([100.0])
    mock_ticker_cls.return_value = mock_t

    s = calculate_sector_strength("XLK", "Technology", 0.0)
    assert s is None


@patch("app.statistics.sectors.yf.Ticker")
def test_calculate_sector_strength_error(mock_ticker_cls):
    mock_ticker_cls.return_value.history.side_effect = RuntimeError("fail")

    s = calculate_sector_strength("XLK", "Technology", 0.0)
    assert s is None


def test_rotation_risk_off():
    """Defensive sectors leading → RISK_OFF."""
    leaders = (
        SectorStrength("XLU", "Utilities", 70, 0.01, 0.02, 0.05, 0.03),
        SectorStrength("XLV", "Healthcare", 140, 0.01, 0.02, 0.04, 0.02),
        SectorStrength("XLI", "Industrials", 110, 0.01, 0.01, 0.03, 0.01),
    )
    laggards = (SectorStrength("XLK", "Tech", 180, -0.01, -0.02, -0.03, -0.05),)
    from app.statistics.sectors import SectorRotation

    rotation = SectorRotation(
        leaders=leaders,
        laggards=laggards,
        rotation_signal="RISK_OFF",
        as_of="",
    )
    assert rotation.rotation_signal == "RISK_OFF"


def test_rotation_risk_on():
    """Growth sectors leading → RISK_ON."""
    leaders = (
        SectorStrength("XLK", "Tech", 180, 0.02, 0.05, 0.08, 0.06),
        SectorStrength("XBI", "Biotech", 90, 0.02, 0.04, 0.07, 0.05),
    )
    from app.statistics.sectors import SectorRotation

    rotation = SectorRotation(
        leaders=leaders,
        laggards=(),
        rotation_signal="RISK_ON",
        as_of="",
    )
    assert rotation.rotation_signal == "RISK_ON"


@patch("app.statistics.sectors.calculate_sector_strength")
@patch("app.statistics.sectors.yf.Ticker")
def test_analyze_sector_rotation(mock_ticker_cls, mock_calc):
    # Mock SPY history
    mock_spy = MagicMock()
    mock_spy.history.return_value = _mock_history([100.0, 105.0])
    mock_ticker_cls.return_value = mock_spy

    # Return None for all sectors (simulates failures)
    mock_calc.return_value = None
    rotation = analyze_sector_rotation()
    assert rotation.rotation_signal == "NEUTRAL"
    assert len(rotation.leaders) == 0
