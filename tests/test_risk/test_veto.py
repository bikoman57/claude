"""Tests for risk veto logic."""

from __future__ import annotations

from app.risk.exposure import ExposureReport
from app.risk.limits import RiskLimits
from app.risk.veto import check_veto


def _make_report(
    *,
    total: float = 10_000.0,
    invested: float = 3_000.0,
    positions: int = 1,
    sector_pcts: dict[str, float] | None = None,
) -> ExposureReport:
    cash = total - invested
    return ExposureReport(
        total_value=total,
        invested_value=invested,
        cash_value=cash,
        invested_pct=invested / total,
        cash_pct=cash / total,
        total_leveraged_exposure=invested * 3,
        leveraged_exposure_ratio=invested * 3 / total,
        sector_exposures={},
        sector_pcts=sector_pcts or {},
        position_count=positions,
    )


def test_no_veto_when_within_limits() -> None:
    """No veto when everything is within limits."""
    report = _make_report(positions=1, sector_pcts={})
    result = check_veto("TQQQ", 1_500.0, report, [])
    assert not result.vetoed
    assert len(result.reasons) == 0


def test_veto_max_positions() -> None:
    """Veto when max positions reached."""
    report = _make_report(positions=4)
    result = check_veto("TQQQ", 1_000.0, report, [])
    assert result.vetoed
    assert any("Max positions" in r for r in result.reasons)


def test_veto_single_position_too_large() -> None:
    """Veto when position exceeds single position limit."""
    report = _make_report()
    limits = RiskLimits(max_single_position_pct=0.10)
    result = check_veto("TQQQ", 2_000.0, report, [], limits=limits)
    assert result.vetoed
    assert any("Position too large" in r for r in result.reasons)


def test_veto_sector_concentration() -> None:
    """Veto when sector would exceed limit."""
    report = _make_report(
        sector_pcts={"nasdaq-100": 0.45},
    )
    limits = RiskLimits(max_sector_exposure_pct=0.50)
    result = check_veto("TQQQ", 1_000.0, report, [], limits=limits)
    assert result.vetoed
    assert any("Sector" in r for r in result.reasons)


def test_veto_cash_reserve() -> None:
    """Veto when cash would drop below minimum."""
    report = _make_report(total=10_000.0, invested=7_500.0)
    result = check_veto("TQQQ", 1_500.0, report, [])
    assert result.vetoed
    assert any("Cash" in r for r in result.reasons)


def test_multiple_veto_reasons() -> None:
    """Can have multiple veto reasons."""
    report = _make_report(
        total=10_000.0,
        invested=7_500.0,
        positions=4,
    )
    result = check_veto("TQQQ", 2_000.0, report, [])
    assert result.vetoed
    assert len(result.reasons) >= 2
