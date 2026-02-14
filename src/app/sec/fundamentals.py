"""Fundamental financial analysis from SEC EDGAR XBRL filings.

Fetches income statement, balance sheet, and cash flow data from the
EDGAR Company Facts API and computes fundamental health metrics.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.sec.holdings import HoldingInfo

_log = logging.getLogger(__name__)

_XBRL_BASE = "https://data.sec.gov/api/xbrl/companyfacts"
_TIMEOUT = 15.0
_CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "sec" / "fundamentals"
)
_DEFAULT_TTL_HOURS = 24

# ---------------------------------------------------------------------------
# XBRL concept aliases — companies use different tags for the same metric
# ---------------------------------------------------------------------------

_CONCEPT_ALIASES: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],
    "total_assets": [
        "Assets",
    ],
    "total_liabilities": [
        "Liabilities",
        "LiabilitiesCurrent",
    ],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "Cash",
    ],
    "total_debt": [
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtNoncurrent",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByOperatingActivities",
    ],
    "capital_expenditure": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    """Financial data for one ticker, one reporting period (from SEC XBRL)."""

    ticker: str
    period_end: str  # ISO YYYY-MM-DD
    period_type: str  # "quarterly" or "annual"
    form_type: str  # "10-K" or "10-Q"
    filed_date: str
    # Income statement
    revenue: float | None
    cost_of_revenue: float | None
    gross_profit: float | None
    operating_income: float | None
    net_income: float | None
    # Balance sheet
    total_assets: float | None
    total_liabilities: float | None
    stockholders_equity: float | None
    cash_and_equivalents: float | None
    total_debt: float | None
    # Cash flow
    operating_cash_flow: float | None
    capital_expenditure: float | None
    free_cash_flow: float | None  # operating_cf - capex (computed)


@dataclass(frozen=True, slots=True)
class FundamentalAnalysis:
    """Derived fundamental metrics and health assessment for one ticker."""

    ticker: str
    latest_period: str
    # Margins (latest quarter)
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    # Growth (YoY — same quarter last year)
    revenue_growth_yoy: float | None
    net_income_growth_yoy: float | None
    # Balance sheet health
    debt_to_equity: float | None
    cash_to_debt: float | None
    # Cash flow quality
    fcf_to_net_income: float | None
    ocf_to_revenue: float | None
    # Trends (current vs year-ago quarter)
    gross_margin_trend: str  # IMPROVING / DECLINING / STABLE
    operating_margin_trend: str
    # Overall classification
    health: str  # STRONG / STABLE / WEAK / DETERIORATING
    health_reasons: tuple[str, ...]


# ---------------------------------------------------------------------------
# XBRL data extraction
# ---------------------------------------------------------------------------


def fetch_company_facts(cik: str, email: str) -> dict[str, Any]:
    """Fetch all XBRL facts for a company from SEC EDGAR."""
    url = f"{_XBRL_BASE}/CIK{cik}.json"
    headers = {"User-Agent": f"fin-agents {email}"}
    with httpx.Client() as client:
        resp = client.get(url, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result


def extract_concept_values(
    facts: dict[str, Any],
    concept_key: str,
) -> list[dict[str, Any]]:
    """Extract XBRL values for a concept, trying aliases in order.

    Returns the USD unit values list from the first matching tag.
    """
    aliases = _CONCEPT_ALIASES.get(concept_key, [])
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    for tag in aliases:
        concept = us_gaap.get(tag)
        if concept is None:
            continue
        units = concept.get("units", {})
        usd_values: list[dict[str, Any]] = units.get("USD", [])
        if usd_values:
            return usd_values

    return []


def _is_quarterly(entry: dict[str, Any]) -> bool:
    """Check if an XBRL entry represents a quarterly period."""
    fp = entry.get("fp", "")
    if fp in ("Q1", "Q2", "Q3", "Q4"):
        return True
    # For income statement items, check duration (~90 days)
    start = entry.get("start")
    end = entry.get("end")
    if start and end:
        with contextlib.suppress(ValueError):
            d_start = date.fromisoformat(start)
            d_end = date.fromisoformat(end)
            days = (d_end - d_start).days
            return 60 <= days <= 120
    return False


def _is_annual(entry: dict[str, Any]) -> bool:
    """Check if an XBRL entry represents an annual period."""
    fp = entry.get("fp", "")
    if fp == "FY":
        return True
    start = entry.get("start")
    end = entry.get("end")
    if start and end:
        with contextlib.suppress(ValueError):
            d_start = date.fromisoformat(start)
            d_end = date.fromisoformat(end)
            days = (d_end - d_start).days
            return 340 <= days <= 400
    return False


def _latest_value_by_period(
    values: list[dict[str, Any]],
    period_filter: str,
    limit: int = 8,
) -> list[tuple[str, float, str, str]]:
    """Get latest values grouped by period end date.

    Returns list of (period_end, value, form_type, filed_date) tuples,
    sorted newest first, limited to `limit` entries.
    """
    checker = _is_quarterly if period_filter == "quarterly" else _is_annual
    seen_periods: dict[str, tuple[float, str, str]] = {}

    for entry in values:
        if not checker(entry):
            continue
        end_date = entry.get("end", "")
        val = entry.get("val")
        form = entry.get("form", "")
        filed = entry.get("filed", "")
        if not end_date or val is None:
            continue
        # Keep most recently filed value for each period
        existing = seen_periods.get(end_date)
        if existing is None or filed > existing[2]:
            seen_periods[end_date] = (float(val), form, filed)

    result = [
        (period, val, form, filed)
        for period, (val, form, filed) in seen_periods.items()
    ]
    result.sort(key=lambda x: x[0], reverse=True)
    return result[:limit]


# ---------------------------------------------------------------------------
# Snapshot building
# ---------------------------------------------------------------------------


def build_snapshots(
    ticker: str,
    facts: dict[str, Any],
    quarters: int = 8,
) -> list[FinancialSnapshot]:
    """Parse XBRL facts into FinancialSnapshot objects.

    Extracts last `quarters` quarterly snapshots. For balance sheet items
    (point-in-time), we match by period_end date. For income/cash flow items
    (period-based), we match quarterly periods.
    """
    # Extract all concept values
    concept_data: dict[str, list[dict[str, Any]]] = {}
    for key in _CONCEPT_ALIASES:
        concept_data[key] = extract_concept_values(facts, key)

    # Determine period end dates from revenue (most reliable income concept)
    revenue_periods = _latest_value_by_period(
        concept_data["revenue"],
        "quarterly",
        limit=quarters,
    )

    if not revenue_periods:
        # Try net income if revenue not available
        revenue_periods = _latest_value_by_period(
            concept_data["net_income"],
            "quarterly",
            limit=quarters,
        )

    if not revenue_periods:
        return []

    # Build a lookup: concept_key -> {period_end: value}
    quarterly_lookup: dict[str, dict[str, float]] = {}
    for key in ("revenue", "cost_of_revenue", "gross_profit", "operating_income",
                "net_income", "operating_cash_flow", "capital_expenditure"):
        periods = _latest_value_by_period(
            concept_data[key], "quarterly", limit=quarters,
        )
        quarterly_lookup[key] = {p[0]: p[1] for p in periods}

    # Balance sheet items are point-in-time — match by end date (any period type)
    bs_lookup: dict[str, dict[str, float]] = {}
    for key in ("total_assets", "total_liabilities", "stockholders_equity",
                "cash_and_equivalents", "total_debt"):
        values = concept_data[key]
        by_end: dict[str, tuple[float, str]] = {}
        for entry in values:
            end_date = entry.get("end", "")
            val = entry.get("val")
            filed = entry.get("filed", "")
            if not end_date or val is None:
                continue
            existing = by_end.get(end_date)
            if existing is None or filed > existing[1]:
                by_end[end_date] = (float(val), filed)
        bs_lookup[key] = {k: v[0] for k, v in by_end.items()}

    snapshots: list[FinancialSnapshot] = []
    for period_end, rev_val, form_type, filed_date in revenue_periods:
        ocf = quarterly_lookup.get("operating_cash_flow", {}).get(period_end)
        capex = quarterly_lookup.get("capital_expenditure", {}).get(period_end)
        fcf: float | None = None
        if ocf is not None and capex is not None:
            fcf = ocf - capex

        snapshots.append(
            FinancialSnapshot(
                ticker=ticker,
                period_end=period_end,
                period_type="quarterly",
                form_type=form_type or "10-Q",
                filed_date=filed_date,
                revenue=rev_val,
                cost_of_revenue=quarterly_lookup.get(
                    "cost_of_revenue", {},
                ).get(period_end),
                gross_profit=quarterly_lookup.get(
                    "gross_profit", {},
                ).get(period_end),
                operating_income=quarterly_lookup.get(
                    "operating_income", {},
                ).get(period_end),
                net_income=quarterly_lookup.get(
                    "net_income", {},
                ).get(period_end),
                total_assets=bs_lookup.get(
                    "total_assets", {},
                ).get(period_end),
                total_liabilities=bs_lookup.get(
                    "total_liabilities", {},
                ).get(period_end),
                stockholders_equity=bs_lookup.get(
                    "stockholders_equity", {},
                ).get(period_end),
                cash_and_equivalents=bs_lookup.get(
                    "cash_and_equivalents", {},
                ).get(period_end),
                total_debt=bs_lookup.get(
                    "total_debt", {},
                ).get(period_end),
                operating_cash_flow=ocf,
                capital_expenditure=capex,
                free_cash_flow=fcf,
            ),
        )

    return snapshots


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Compute ratio, returning None if inputs missing or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _safe_growth(current: float | None, prior: float | None) -> float | None:
    """Compute YoY growth rate, returning None if data missing."""
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def _classify_trend(
    current: float | None,
    prior: float | None,
    threshold: float = 0.02,
) -> str:
    """Classify a trend as IMPROVING, DECLINING, or STABLE."""
    if current is None or prior is None:
        return "STABLE"
    diff = current - prior
    if diff > threshold:
        return "IMPROVING"
    if diff < -threshold:
        return "DECLINING"
    return "STABLE"


def analyze_fundamentals(snapshots: list[FinancialSnapshot]) -> FundamentalAnalysis:
    """Compute fundamental analysis from quarterly snapshots.

    Expects snapshots sorted newest-first.
    """
    if not snapshots:
        return FundamentalAnalysis(
            ticker="",
            latest_period="",
            gross_margin=None,
            operating_margin=None,
            net_margin=None,
            revenue_growth_yoy=None,
            net_income_growth_yoy=None,
            debt_to_equity=None,
            cash_to_debt=None,
            fcf_to_net_income=None,
            ocf_to_revenue=None,
            gross_margin_trend="STABLE",
            operating_margin_trend="STABLE",
            health="STABLE",
            health_reasons=("Insufficient data",),
        )

    latest = snapshots[0]

    # Margins (latest quarter)
    gross_margin = _safe_ratio(latest.gross_profit, latest.revenue)
    operating_margin = _safe_ratio(latest.operating_income, latest.revenue)
    net_margin = _safe_ratio(latest.net_income, latest.revenue)

    # YoY growth — find quarter from ~1 year ago
    yoy_quarter: FinancialSnapshot | None = None
    for s in snapshots[3:5]:  # 4th or 5th quarter back is ~1 year ago
        yoy_quarter = s
        break

    revenue_growth = _safe_growth(
        latest.revenue,
        yoy_quarter.revenue if yoy_quarter else None,
    )
    ni_growth = _safe_growth(
        latest.net_income,
        yoy_quarter.net_income if yoy_quarter else None,
    )

    # Balance sheet ratios
    debt_to_equity = _safe_ratio(latest.total_debt, latest.stockholders_equity)
    cash_to_debt = _safe_ratio(latest.cash_and_equivalents, latest.total_debt)

    # Cash flow quality
    fcf_to_ni = _safe_ratio(latest.free_cash_flow, latest.net_income)
    ocf_to_rev = _safe_ratio(latest.operating_cash_flow, latest.revenue)

    # Margin trends (current vs year-ago quarter)
    prior_gm = _safe_ratio(
        yoy_quarter.gross_profit if yoy_quarter else None,
        yoy_quarter.revenue if yoy_quarter else None,
    )
    prior_om = _safe_ratio(
        yoy_quarter.operating_income if yoy_quarter else None,
        yoy_quarter.revenue if yoy_quarter else None,
    )
    gm_trend = _classify_trend(gross_margin, prior_gm)
    om_trend = _classify_trend(operating_margin, prior_om)

    # Health classification
    health, reasons = _classify_health(
        revenue_growth=revenue_growth,
        gross_margin=gross_margin,
        operating_margin=operating_margin,
        gm_trend=gm_trend,
        om_trend=om_trend,
        debt_to_equity=debt_to_equity,
        fcf_to_ni=fcf_to_ni,
        net_income=latest.net_income,
        free_cash_flow=latest.free_cash_flow,
    )

    return FundamentalAnalysis(
        ticker=latest.ticker,
        latest_period=latest.period_end,
        gross_margin=gross_margin,
        operating_margin=operating_margin,
        net_margin=net_margin,
        revenue_growth_yoy=revenue_growth,
        net_income_growth_yoy=ni_growth,
        debt_to_equity=debt_to_equity,
        cash_to_debt=cash_to_debt,
        fcf_to_net_income=fcf_to_ni,
        ocf_to_revenue=ocf_to_rev,
        gross_margin_trend=gm_trend,
        operating_margin_trend=om_trend,
        health=health,
        health_reasons=tuple(reasons),
    )


def _classify_health(
    *,
    revenue_growth: float | None,
    gross_margin: float | None,
    operating_margin: float | None,
    gm_trend: str,
    om_trend: str,
    debt_to_equity: float | None,
    fcf_to_ni: float | None,
    net_income: float | None,
    free_cash_flow: float | None,
) -> tuple[str, list[str]]:
    """Classify overall fundamental health.

    Returns (health_level, list_of_reasons).
    """
    reasons: list[str] = []
    strong_signals = 0
    weak_signals = 0

    # Revenue growth
    if revenue_growth is not None:
        if revenue_growth > 0.05:
            strong_signals += 1
            reasons.append(f"Revenue growing {revenue_growth:+.0%} YoY")
        elif revenue_growth < -0.05:
            weak_signals += 1
            reasons.append(f"Revenue declining {revenue_growth:+.0%} YoY")

    # Margins
    if gross_margin is not None and gross_margin > 0.3:
        strong_signals += 1
    if operating_margin is not None:
        if operating_margin > 0.15:
            strong_signals += 1
            reasons.append(f"Operating margin {operating_margin:.0%}")
        elif operating_margin < 0:
            weak_signals += 1
            reasons.append(f"Negative operating margin {operating_margin:.0%}")

    # Margin trends
    if gm_trend == "DECLINING" and om_trend == "DECLINING":
        weak_signals += 1
        reasons.append("Margins declining YoY")
    elif gm_trend == "IMPROVING" or om_trend == "IMPROVING":
        strong_signals += 1
        reasons.append("Margins improving YoY")

    # Leverage
    if debt_to_equity is not None:
        if debt_to_equity > 3.0:
            weak_signals += 1
            reasons.append(f"High leverage: D/E {debt_to_equity:.1f}")
        elif debt_to_equity < 1.5:
            strong_signals += 1

    # Cash flow quality
    if fcf_to_ni is not None and fcf_to_ni > 0.8:
        strong_signals += 1
        reasons.append("Earnings backed by cash flow")
    elif free_cash_flow is not None and free_cash_flow < 0:
        weak_signals += 1
        reasons.append("Negative free cash flow")

    # Profitability
    if net_income is not None and net_income < 0:
        weak_signals += 1
        reasons.append("Net loss")

    # Classify
    if weak_signals >= 3:
        return "WEAK", reasons
    if (revenue_growth is not None and revenue_growth < -0.05
            and (gm_trend == "DECLINING" or om_trend == "DECLINING")):
        return "DETERIORATING", reasons
    if strong_signals >= 4 and weak_signals == 0:
        return "STRONG", reasons
    if strong_signals >= 3:
        return "STRONG", reasons

    if not reasons:
        reasons.append("Mixed fundamental indicators")
    return "STABLE", reasons


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def _is_cache_stale(ticker: str, ttl_hours: int = _DEFAULT_TTL_HOURS) -> bool:
    """Check if cached fundamentals for a ticker are stale."""
    meta_path = _CACHE_DIR / "fetch_meta.json"
    if not meta_path.exists():
        return True
    with contextlib.suppress(Exception):
        meta = json.loads(meta_path.read_text())
        last_fetch = meta.get(ticker, {}).get("fetched_at", "")
        if last_fetch:
            fetched = datetime.fromisoformat(last_fetch)
            return datetime.now(tz=UTC) - fetched > timedelta(hours=ttl_hours)
    return True


def _read_cache(ticker: str) -> FundamentalAnalysis | None:
    """Read cached analysis for a ticker."""
    cache_file = _CACHE_DIR / f"{ticker}.json"
    if not cache_file.exists():
        return None
    with contextlib.suppress(Exception):
        data = json.loads(cache_file.read_text())
        return FundamentalAnalysis(
            ticker=data["ticker"],
            latest_period=data["latest_period"],
            gross_margin=data.get("gross_margin"),
            operating_margin=data.get("operating_margin"),
            net_margin=data.get("net_margin"),
            revenue_growth_yoy=data.get("revenue_growth_yoy"),
            net_income_growth_yoy=data.get("net_income_growth_yoy"),
            debt_to_equity=data.get("debt_to_equity"),
            cash_to_debt=data.get("cash_to_debt"),
            fcf_to_net_income=data.get("fcf_to_net_income"),
            ocf_to_revenue=data.get("ocf_to_revenue"),
            gross_margin_trend=data.get("gross_margin_trend", "STABLE"),
            operating_margin_trend=data.get("operating_margin_trend", "STABLE"),
            health=data.get("health", "STABLE"),
            health_reasons=tuple(data.get("health_reasons", [])),
        )
    return None


def _write_cache(ticker: str, analysis: FundamentalAnalysis) -> None:
    """Write analysis to cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / f"{ticker}.json"
    cache_file.write_text(json.dumps(asdict(analysis), indent=2))

    # Update fetch metadata
    meta_path = _CACHE_DIR / "fetch_meta.json"
    meta: dict[str, Any] = {}
    if meta_path.exists():
        with contextlib.suppress(Exception):
            meta = json.loads(meta_path.read_text())
    meta[ticker] = {"fetched_at": datetime.now(tz=UTC).isoformat()}
    meta_path.write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_and_analyze(
    ticker: str,
    cik: str,
    email: str,
) -> FundamentalAnalysis:
    """Full pipeline: fetch XBRL data, build snapshots, analyze fundamentals."""
    # Check cache first
    if not _is_cache_stale(ticker):
        cached = _read_cache(ticker)
        if cached is not None:
            return cached

    facts = fetch_company_facts(cik, email)
    snapshots = build_snapshots(ticker, facts)
    analysis = analyze_fundamentals(snapshots)

    _write_cache(ticker, analysis)
    return analysis


def fetch_all_fundamentals(
    holdings: list[HoldingInfo],
    email: str,
) -> list[FundamentalAnalysis]:
    """Fetch and analyze fundamentals for all holdings, skipping failures."""
    results: list[FundamentalAnalysis] = []
    for h in holdings:
        with contextlib.suppress(Exception):
            analysis = fetch_and_analyze(h.ticker, h.cik, email)
            results.append(analysis)
        time.sleep(0.1)  # SEC rate limit
    return results


def classify_sector_health(analyses: list[FundamentalAnalysis]) -> str:
    """Classify sector health by majority vote of constituent holdings."""
    if not analyses:
        return "STABLE"

    counts: dict[str, int] = {"STRONG": 0, "STABLE": 0, "WEAK": 0, "DETERIORATING": 0}
    for a in analyses:
        counts[a.health] = counts.get(a.health, 0) + 1

    # WEAK + DETERIORATING together count as negative
    negative = counts["WEAK"] + counts["DETERIORATING"]
    positive = counts["STRONG"]
    total = len(analyses)

    if negative > total / 2:
        return "WEAK"
    if positive > total / 2:
        return "STRONG"
    if counts["DETERIORATING"] > total / 3:
        return "DETERIORATING"
    return "STABLE"
