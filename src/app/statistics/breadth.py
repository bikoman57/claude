from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf


@dataclass(frozen=True, slots=True)
class VolumeSpike:
    """Unusual volume detection for one ticker."""

    ticker: str
    current_volume: int
    avg_volume_20d: float
    volume_ratio: float


@dataclass(frozen=True, slots=True)
class MarketBreadth:
    """Market breadth indicators."""

    put_call_ratio: float | None
    vix_term_structure: str
    unusual_volume_tickers: tuple[str, ...]
    as_of: str


def fetch_put_call_ratio() -> float | None:
    """Fetch CBOE equity put/call ratio."""
    try:
        t = yf.Ticker("^PCCE")
        hist = t.history(period="5d")
        if len(hist) > 0:
            return float(hist["Close"].iloc[-1])
    except Exception:  # noqa: S110
        pass
    return None


def analyze_vix_term_structure() -> str:
    """Compare VIX to VIX3M for term structure classification."""
    try:
        vix = yf.Ticker("^VIX")
        vix3m = yf.Ticker("^VIX3M")
        vix_hist = vix.history(period="5d")
        vix3m_hist = vix3m.history(period="5d")

        if len(vix_hist) > 0 and len(vix3m_hist) > 0:
            vix_val = float(vix_hist["Close"].iloc[-1])
            vix3m_val = float(vix3m_hist["Close"].iloc[-1])

            if vix_val < vix3m_val * 0.95:
                return "CONTANGO"
            if vix_val > vix3m_val * 1.05:
                return "BACKWARDATION"
            return "FLAT"
    except Exception:  # noqa: S110
        pass
    return "UNKNOWN"


def detect_volume_spikes(
    tickers: list[str],
    threshold: float = 2.0,
) -> list[VolumeSpike]:
    """Detect unusual volume across given tickers."""
    spikes: list[VolumeSpike] = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1mo")
            if len(hist) < 5:
                continue

            volumes = hist["Volume"]
            current = int(volumes.iloc[-1])
            avg_20d = float(volumes.iloc[:-1].mean())
            if avg_20d <= 0:
                continue

            ratio = current / avg_20d
            if ratio >= threshold:
                spikes.append(
                    VolumeSpike(
                        ticker=ticker,
                        current_volume=current,
                        avg_volume_20d=avg_20d,
                        volume_ratio=ratio,
                    ),
                )
        except Exception:  # noqa: S112
            continue
    return spikes


def analyze_market_breadth(
    volume_tickers: list[str] | None = None,
) -> MarketBreadth:
    """Build complete market breadth analysis."""
    pcr = fetch_put_call_ratio()
    vix_term = analyze_vix_term_structure()

    tickers = volume_tickers or ["SPY", "QQQ", "IWM", "DIA"]
    spikes = detect_volume_spikes(tickers)
    spike_names = tuple(s.ticker for s in spikes)

    return MarketBreadth(
        put_call_ratio=pcr,
        vix_term_structure=vix_term,
        unusual_volume_tickers=spike_names,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
