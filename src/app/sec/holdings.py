from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HoldingInfo:
    """A stock holding in an index ETF."""

    ticker: str
    name: str
    cik: str  # SEC CIK, zero-padded to 10 digits


INDEX_HOLDINGS: dict[str, list[HoldingInfo]] = {
    "QQQ": [
        HoldingInfo("AAPL", "Apple Inc.", "0000320193"),
        HoldingInfo("MSFT", "Microsoft Corp.", "0000789019"),
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AMZN", "Amazon.com Inc.", "0001018724"),
        HoldingInfo("META", "Meta Platforms Inc.", "0001326801"),
        HoldingInfo("GOOGL", "Alphabet Inc.", "0001652044"),
        HoldingInfo("TSLA", "Tesla Inc.", "0001318605"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
    ],
    "SPY": [
        HoldingInfo("AAPL", "Apple Inc.", "0000320193"),
        HoldingInfo("MSFT", "Microsoft Corp.", "0000789019"),
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AMZN", "Amazon.com Inc.", "0001018724"),
        HoldingInfo("META", "Meta Platforms Inc.", "0001326801"),
        HoldingInfo("GOOGL", "Alphabet Inc.", "0001652044"),
        HoldingInfo("BRK-B", "Berkshire Hathaway Inc.", "0001067983"),
        HoldingInfo("JPM", "JPMorgan Chase & Co.", "0000019617"),
    ],
    "SOXX": [
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AMD", "Advanced Micro Devices", "0000002488"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
        HoldingInfo("QCOM", "Qualcomm Inc.", "0000804328"),
        HoldingInfo("TXN", "Texas Instruments Inc.", "0000097476"),
        HoldingInfo("INTC", "Intel Corp.", "0000050863"),
        HoldingInfo("MU", "Micron Technology Inc.", "0000723125"),
        HoldingInfo("AMAT", "Applied Materials Inc.", "0000006951"),
    ],
    "IWM": [],  # Russell 2000 — too many holdings
    "XLK": [
        HoldingInfo("AAPL", "Apple Inc.", "0000320193"),
        HoldingInfo("MSFT", "Microsoft Corp.", "0000789019"),
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
        HoldingInfo("CRM", "Salesforce Inc.", "0001108524"),
    ],
    "XLF": [
        HoldingInfo("BRK-B", "Berkshire Hathaway Inc.", "0001067983"),
        HoldingInfo("JPM", "JPMorgan Chase & Co.", "0000019617"),
        HoldingInfo("V", "Visa Inc.", "0001403161"),
        HoldingInfo("MA", "Mastercard Inc.", "0001141391"),
        HoldingInfo("BAC", "Bank of America Corp.", "0000070858"),
    ],
    "XBI": [
        HoldingInfo("VRTX", "Vertex Pharmaceuticals", "0000875320"),
        HoldingInfo("REGN", "Regeneron Pharmaceuticals", "0000872589"),
        HoldingInfo("MRNA", "Moderna Inc.", "0001682852"),
    ],
    "USO": [],  # Oil commodity ETF — no equity holdings
}


def get_holdings(underlying: str) -> list[HoldingInfo]:
    """Get top holdings for an underlying index ETF."""
    return INDEX_HOLDINGS.get(underlying.upper(), [])


def get_holding_by_ticker(ticker: str) -> HoldingInfo | None:
    """Look up a holding by its stock ticker."""
    for holdings in INDEX_HOLDINGS.values():
        for h in holdings:
            if h.ticker == ticker.upper():
                return h
    return None


def get_all_unique_holdings() -> list[HoldingInfo]:
    """Get all unique holdings across all indices (deduplicated)."""
    seen: set[str] = set()
    result: list[HoldingInfo] = []
    for holdings in INDEX_HOLDINGS.values():
        for h in holdings:
            if h.ticker not in seen:
                seen.add(h.ticker)
                result.append(h)
    return result
