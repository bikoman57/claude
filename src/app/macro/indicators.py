from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import yfinance as yf
from dotenv import load_dotenv

_FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


@dataclass(frozen=True, slots=True)
class MacroDashboard:
    """Macro indicators dashboard."""

    vix: float
    vix_regime: str
    cpi_yoy: float | None
    unemployment: float | None
    gdp_growth: float | None
    fed_funds_rate: float | None
    as_of: str


def classify_vix(vix: float) -> str:
    """Classify VIX into regime."""
    if vix < 15:
        return "LOW"
    if vix < 20:
        return "NORMAL"
    if vix < 30:
        return "ELEVATED"
    return "EXTREME"


def fetch_vix() -> float:
    """Fetch current VIX from yfinance."""
    t = yf.Ticker("^VIX")
    hist = t.history(period="5d")
    if hist.empty:
        msg = "No VIX data available"
        raise ValueError(msg)
    return float(hist["Close"].iloc[-1])


def fetch_fred_latest(
    series_id: str,
    api_key: str,
    units: str = "",
) -> float | None:
    """Fetch latest value from a FRED series."""
    params: dict[str, str] = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": "1",
    }
    if units:
        params["units"] = units
    with httpx.Client() as client:
        resp = client.get(
            _FRED_BASE,
            params=params,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    observations = data.get("observations", [])
    if not observations:
        return None
    value = observations[0].get("value", ".")
    return None if value == "." else float(value)


def fetch_fred_history(
    series_id: str,
    api_key: str,
    limit: int = 6,
) -> list[float]:
    """Fetch last N values from a FRED series (oldest first)."""
    params: dict[str, str] = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": str(limit),
    }
    with httpx.Client() as client:
        resp = client.get(
            _FRED_BASE,
            params=params,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    observations = data.get("observations", [])
    values: list[float] = []
    for obs in reversed(observations):
        val = obs.get("value", ".")
        if val != ".":
            values.append(float(val))
    return values


def fetch_dashboard() -> MacroDashboard:
    """Fetch full macro dashboard."""
    load_dotenv()
    vix = fetch_vix()
    fred_key = os.environ.get("FRED_API_KEY", "")
    cpi = None
    unemployment = None
    gdp = None
    fed_rate = None

    if fred_key:
        cpi = fetch_fred_latest("CPIAUCSL", fred_key, units="pc1")
        unemployment = fetch_fred_latest("UNRATE", fred_key)
        gdp = fetch_fred_latest("A191RL1Q225SBEA", fred_key)
        fed_rate = fetch_fred_latest("FEDFUNDS", fred_key)

    return MacroDashboard(
        vix=vix,
        vix_regime=classify_vix(vix),
        cpi_yoy=cpi,
        unemployment=unemployment,
        gdp_growth=gdp,
        fed_funds_rate=fed_rate,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
