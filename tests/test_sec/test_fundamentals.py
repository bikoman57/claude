"""Tests for SEC EDGAR XBRL fundamental financial analysis."""

from __future__ import annotations

from app.sec.fundamentals import (
    FinancialSnapshot,
    FundamentalAnalysis,
    analyze_fundamentals,
    build_snapshots,
    classify_sector_health,
    extract_concept_values,
)

# ---------------------------------------------------------------------------
# Helpers to build mock XBRL data
# ---------------------------------------------------------------------------


def _make_xbrl_entry(
    end: str,
    val: float,
    form: str = "10-Q",
    filed: str = "2025-01-15",
    fp: str = "Q1",
    start: str | None = None,
) -> dict:
    entry: dict = {"end": end, "val": val, "form": form, "filed": filed, "fp": fp}
    if start:
        entry["start"] = start
    return entry


def _make_facts(concepts: dict[str, list[dict]]) -> dict:
    """Build a minimal companyfacts-style dict."""
    us_gaap = {}
    for tag, entries in concepts.items():
        us_gaap[tag] = {"units": {"USD": entries}}
    return {"facts": {"us-gaap": us_gaap}}


def _make_snapshot(
    ticker: str = "AAPL",
    period_end: str = "2025-03-31",
    revenue: float | None = 100_000,
    gross_profit: float | None = 45_000,
    operating_income: float | None = 30_000,
    net_income: float | None = 25_000,
    total_debt: float | None = 50_000,
    stockholders_equity: float | None = 80_000,
    cash_and_equivalents: float | None = 60_000,
    operating_cash_flow: float | None = 35_000,
    capital_expenditure: float | None = 10_000,
    free_cash_flow: float | None = 25_000,
    **kwargs: object,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        ticker=ticker,
        period_end=period_end,
        period_type="quarterly",
        form_type="10-Q",
        filed_date="2025-04-15",
        revenue=revenue,
        cost_of_revenue=kwargs.get("cost_of_revenue", 55_000),  # type: ignore[arg-type]
        gross_profit=gross_profit,
        operating_income=operating_income,
        net_income=net_income,
        total_assets=kwargs.get("total_assets", 200_000),  # type: ignore[arg-type]
        total_liabilities=kwargs.get("total_liabilities", 120_000),  # type: ignore[arg-type]
        stockholders_equity=stockholders_equity,
        cash_and_equivalents=cash_and_equivalents,
        total_debt=total_debt,
        operating_cash_flow=operating_cash_flow,
        capital_expenditure=capital_expenditure,
        free_cash_flow=free_cash_flow,
    )


# ---------------------------------------------------------------------------
# extract_concept_values
# ---------------------------------------------------------------------------


class TestExtractConcept:
    def test_primary_tag(self) -> None:
        facts = _make_facts({
            "Revenues": [_make_xbrl_entry("2025-03-31", 100_000)],
        })
        result = extract_concept_values(facts, "revenue")
        assert len(result) == 1
        assert result[0]["val"] == 100_000

    def test_alias_fallback(self) -> None:
        facts = _make_facts({
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                _make_xbrl_entry("2025-03-31", 200_000),
            ],
        })
        result = extract_concept_values(facts, "revenue")
        assert len(result) == 1
        assert result[0]["val"] == 200_000

    def test_primary_preferred_over_alias(self) -> None:
        facts = _make_facts({
            "Revenues": [_make_xbrl_entry("2025-03-31", 100_000)],
            "SalesRevenueNet": [_make_xbrl_entry("2025-03-31", 99_000)],
        })
        result = extract_concept_values(facts, "revenue")
        assert result[0]["val"] == 100_000

    def test_missing_concept(self) -> None:
        facts = _make_facts({})
        result = extract_concept_values(facts, "revenue")
        assert result == []

    def test_empty_usd_values(self) -> None:
        facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": []}}}}}
        result = extract_concept_values(facts, "revenue")
        assert result == []


# ---------------------------------------------------------------------------
# build_snapshots
# ---------------------------------------------------------------------------


class TestBuildSnapshots:
    def test_quarterly_snapshots(self) -> None:
        facts = _make_facts({
            "Revenues": [
                _make_xbrl_entry("2025-03-31", 100_000, fp="Q1",
                                 start="2025-01-01", filed="2025-04-15"),
                _make_xbrl_entry("2024-12-31", 95_000, fp="Q4",
                                 start="2024-10-01", filed="2025-01-15"),
                _make_xbrl_entry("2024-09-30", 90_000, fp="Q3",
                                 start="2024-07-01", filed="2024-10-15"),
                _make_xbrl_entry("2024-06-30", 85_000, fp="Q2",
                                 start="2024-04-01", filed="2024-07-15"),
            ],
            "NetIncomeLoss": [
                _make_xbrl_entry("2025-03-31", 25_000, fp="Q1",
                                 start="2025-01-01", filed="2025-04-15"),
                _make_xbrl_entry("2024-12-31", 23_000, fp="Q4",
                                 start="2024-10-01", filed="2025-01-15"),
            ],
        })
        snapshots = build_snapshots("AAPL", facts)
        assert len(snapshots) == 4
        assert snapshots[0].period_end == "2025-03-31"
        assert snapshots[0].revenue == 100_000
        assert snapshots[0].net_income == 25_000
        # Older quarter should have net income too
        assert snapshots[1].net_income == 23_000

    def test_empty_facts(self) -> None:
        facts = _make_facts({})
        snapshots = build_snapshots("AAPL", facts)
        assert snapshots == []

    def test_balance_sheet_matched(self) -> None:
        facts = _make_facts({
            "Revenues": [
                _make_xbrl_entry("2025-03-31", 100_000, fp="Q1",
                                 start="2025-01-01"),
            ],
            "Assets": [
                _make_xbrl_entry("2025-03-31", 500_000, fp="Q1"),
            ],
            "StockholdersEquity": [
                _make_xbrl_entry("2025-03-31", 200_000, fp="Q1"),
            ],
        })
        snapshots = build_snapshots("AAPL", facts)
        assert len(snapshots) == 1
        assert snapshots[0].total_assets == 500_000
        assert snapshots[0].stockholders_equity == 200_000


# ---------------------------------------------------------------------------
# analyze_fundamentals
# ---------------------------------------------------------------------------


class TestAnalyzeMargins:
    def test_margins_computed(self) -> None:
        snap = _make_snapshot(revenue=100_000, gross_profit=45_000,
                              operating_income=30_000, net_income=25_000)
        result = analyze_fundamentals([snap])
        assert result.gross_margin is not None
        assert abs(result.gross_margin - 0.45) < 0.001
        assert result.operating_margin is not None
        assert abs(result.operating_margin - 0.30) < 0.001
        assert result.net_margin is not None
        assert abs(result.net_margin - 0.25) < 0.001

    def test_margins_none_with_no_revenue(self) -> None:
        snap = _make_snapshot(revenue=None, gross_profit=45_000)
        result = analyze_fundamentals([snap])
        assert result.gross_margin is None
        assert result.operating_margin is None

    def test_zero_revenue(self) -> None:
        snap = _make_snapshot(
            revenue=0, gross_profit=0,
            operating_income=0, net_income=0,
        )
        result = analyze_fundamentals([snap])
        assert result.gross_margin is None  # 0/0 = None


class TestAnalyzeGrowth:
    def test_yoy_growth(self) -> None:
        current = _make_snapshot(
            period_end="2025-03-31",
            revenue=120_000, net_income=30_000,
        )
        q3 = _make_snapshot(period_end="2024-12-31", revenue=110_000)
        q2 = _make_snapshot(period_end="2024-09-30", revenue=105_000)
        q1 = _make_snapshot(period_end="2024-06-30", revenue=100_000)
        year_ago = _make_snapshot(
            period_end="2024-03-31",
            revenue=100_000, net_income=25_000,
        )

        result = analyze_fundamentals([current, q3, q2, q1, year_ago])
        assert result.revenue_growth_yoy is not None
        # Growth is current/year_ago: (100_000 - 100_000) / 100_000 = 0.0
        # But year_ago is at index 4, and code picks from snapshots[3:5]
        # so q1 (index 3) at 100_000 is the comparator
        assert abs(result.revenue_growth_yoy - 0.20) < 0.01

    def test_no_yoy_data(self) -> None:
        current = _make_snapshot(period_end="2025-03-31", revenue=120_000)
        result = analyze_fundamentals([current])
        assert result.revenue_growth_yoy is None


class TestAnalyzeBalanceSheet:
    def test_debt_to_equity(self) -> None:
        snap = _make_snapshot(total_debt=100_000, stockholders_equity=200_000)
        result = analyze_fundamentals([snap])
        assert result.debt_to_equity is not None
        assert abs(result.debt_to_equity - 0.5) < 0.001

    def test_cash_to_debt(self) -> None:
        snap = _make_snapshot(cash_and_equivalents=150_000, total_debt=100_000)
        result = analyze_fundamentals([snap])
        assert result.cash_to_debt is not None
        assert abs(result.cash_to_debt - 1.5) < 0.001

    def test_no_equity(self) -> None:
        snap = _make_snapshot(total_debt=100_000, stockholders_equity=None)
        result = analyze_fundamentals([snap])
        assert result.debt_to_equity is None


class TestAnalyzeCashFlow:
    def test_fcf_quality(self) -> None:
        snap = _make_snapshot(
            free_cash_flow=30_000, net_income=25_000,
            operating_cash_flow=40_000, revenue=100_000,
        )
        result = analyze_fundamentals([snap])
        assert result.fcf_to_net_income is not None
        assert abs(result.fcf_to_net_income - 1.2) < 0.001
        assert result.ocf_to_revenue is not None
        assert abs(result.ocf_to_revenue - 0.4) < 0.001


# ---------------------------------------------------------------------------
# Health classification
# ---------------------------------------------------------------------------


class TestHealthClassification:
    def test_strong(self) -> None:
        """Revenue growing, margins improving, low debt, good cash flow."""
        current = _make_snapshot(
            period_end="2025-03-31",
            revenue=120_000, gross_profit=60_000, operating_income=30_000,
            net_income=25_000, total_debt=50_000, stockholders_equity=200_000,
            free_cash_flow=30_000, operating_cash_flow=40_000,
        )
        year_ago = _make_snapshot(
            period_end="2024-03-31",
            revenue=100_000, gross_profit=45_000, operating_income=22_000,
            net_income=18_000,
        )
        # Fill quarters between
        q3 = _make_snapshot(period_end="2024-12-31", revenue=115_000)
        q2 = _make_snapshot(period_end="2024-09-30", revenue=110_000)
        q1 = _make_snapshot(period_end="2024-06-30", revenue=105_000)

        result = analyze_fundamentals([current, q3, q2, q1, year_ago])
        assert result.health == "STRONG"

    def test_weak_negative_growth_bad_margins(self) -> None:
        """Revenue declining, negative operating margin, high debt."""
        current = _make_snapshot(
            period_end="2025-03-31",
            revenue=80_000, gross_profit=15_000, operating_income=-5_000,
            net_income=-10_000, total_debt=500_000, stockholders_equity=100_000,
            free_cash_flow=-15_000, operating_cash_flow=-5_000,
        )
        year_ago = _make_snapshot(
            period_end="2024-03-31",
            revenue=100_000, gross_profit=30_000, operating_income=10_000,
            net_income=5_000,
        )
        q3 = _make_snapshot(period_end="2024-12-31", revenue=90_000)
        q2 = _make_snapshot(period_end="2024-09-30", revenue=95_000)
        q1 = _make_snapshot(period_end="2024-06-30", revenue=98_000)

        result = analyze_fundamentals([current, q3, q2, q1, year_ago])
        assert result.health in ("WEAK", "DETERIORATING")

    def test_deteriorating(self) -> None:
        """Revenue declining AND margins declining."""
        current = _make_snapshot(
            period_end="2025-03-31",
            revenue=90_000, gross_profit=27_000, operating_income=10_000,
            net_income=8_000, total_debt=50_000, stockholders_equity=150_000,
            free_cash_flow=12_000, operating_cash_flow=15_000,
        )
        year_ago = _make_snapshot(
            period_end="2024-03-31",
            revenue=100_000, gross_profit=40_000, operating_income=20_000,
            net_income=15_000,
        )
        q3 = _make_snapshot(period_end="2024-12-31", revenue=95_000)
        q2 = _make_snapshot(period_end="2024-09-30", revenue=97_000)
        q1 = _make_snapshot(period_end="2024-06-30", revenue=99_000)

        result = analyze_fundamentals([current, q3, q2, q1, year_ago])
        assert result.health == "DETERIORATING"

    def test_stable_mixed_signals(self) -> None:
        """Some good, some bad — overall stable."""
        current = _make_snapshot(
            period_end="2025-03-31",
            revenue=102_000, gross_profit=22_000, operating_income=10_000,
            net_income=7_000, total_debt=200_000, stockholders_equity=100_000,
            free_cash_flow=-2_000, operating_cash_flow=8_000,
        )
        year_ago = _make_snapshot(
            period_end="2024-03-31",
            revenue=100_000, gross_profit=22_000, operating_income=10_000,
            net_income=7_000,
        )
        q3 = _make_snapshot(period_end="2024-12-31", revenue=101_000)
        q2 = _make_snapshot(period_end="2024-09-30", revenue=100_500)
        q1 = _make_snapshot(period_end="2024-06-30", revenue=100_200)

        result = analyze_fundamentals([current, q3, q2, q1, year_ago])
        assert result.health == "STABLE"

    def test_empty_snapshots(self) -> None:
        result = analyze_fundamentals([])
        assert result.health == "STABLE"
        assert "Insufficient data" in result.health_reasons


# ---------------------------------------------------------------------------
# Missing data handling
# ---------------------------------------------------------------------------


class TestMissingData:
    def test_all_none(self) -> None:
        snap = FinancialSnapshot(
            ticker="TEST", period_end="2025-03-31", period_type="quarterly",
            form_type="10-Q", filed_date="2025-04-15",
            revenue=None, cost_of_revenue=None, gross_profit=None,
            operating_income=None, net_income=None,
            total_assets=None, total_liabilities=None,
            stockholders_equity=None, cash_and_equivalents=None,
            total_debt=None, operating_cash_flow=None,
            capital_expenditure=None, free_cash_flow=None,
        )
        result = analyze_fundamentals([snap])
        assert result.gross_margin is None
        assert result.debt_to_equity is None
        assert result.health == "STABLE"


# ---------------------------------------------------------------------------
# Sector health classification
# ---------------------------------------------------------------------------


class TestSectorHealth:
    def _analysis(self, health: str) -> FundamentalAnalysis:
        return FundamentalAnalysis(
            ticker="TEST", latest_period="2025-03-31",
            gross_margin=None, operating_margin=None, net_margin=None,
            revenue_growth_yoy=None, net_income_growth_yoy=None,
            debt_to_equity=None, cash_to_debt=None,
            fcf_to_net_income=None, ocf_to_revenue=None,
            gross_margin_trend="STABLE", operating_margin_trend="STABLE",
            health=health, health_reasons=(),
        )

    def test_majority_strong(self) -> None:
        analyses = [self._analysis("STRONG")] * 3 + [self._analysis("STABLE")]
        assert classify_sector_health(analyses) == "STRONG"

    def test_majority_weak(self) -> None:
        analyses = [self._analysis("WEAK")] * 3 + [self._analysis("STABLE")]
        assert classify_sector_health(analyses) == "WEAK"

    def test_mixed_stable(self) -> None:
        analyses = [
            self._analysis("STRONG"),
            self._analysis("STABLE"),
            self._analysis("WEAK"),
            self._analysis("STABLE"),
        ]
        assert classify_sector_health(analyses) == "STABLE"

    def test_empty(self) -> None:
        assert classify_sector_health([]) == "STABLE"

    def test_deteriorating_count(self) -> None:
        analyses = [self._analysis("DETERIORATING")] * 2 + [
            self._analysis("STABLE"),
            self._analysis("STRONG"),
        ]
        assert classify_sector_health(analyses) == "DETERIORATING"
