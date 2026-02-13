from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HoldingInfo:
    """A stock holding in an index ETF."""

    ticker: str
    name: str
    cik: str  # SEC CIK, zero-padded to 10 digits


INDEX_HOLDINGS: dict[str, list[HoldingInfo]] = {
    # --- Nasdaq-100 / QQQ ---
    "QQQ": [
        HoldingInfo("AAPL", "Apple Inc.", "0000320193"),
        HoldingInfo("MSFT", "Microsoft Corp.", "0000789019"),
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AMZN", "Amazon.com Inc.", "0001018724"),
        HoldingInfo("META", "Meta Platforms Inc.", "0001326801"),
        HoldingInfo("GOOGL", "Alphabet Inc.", "0001652044"),
        HoldingInfo("GOOG", "Alphabet Inc. Class C", "0001652044"),
        HoldingInfo("TSLA", "Tesla Inc.", "0001318605"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
        HoldingInfo("NFLX", "Netflix Inc.", "0001065280"),
        HoldingInfo("CRM", "Salesforce Inc.", "0001108524"),
        HoldingInfo("ADBE", "Adobe Inc.", "0000796343"),
        HoldingInfo("ORCL", "Oracle Corp.", "0001341439"),
        HoldingInfo("CSCO", "Cisco Systems Inc.", "0000858877"),
        HoldingInfo("IBM", "International Business Machines", "0000051143"),
        HoldingInfo("NOW", "ServiceNow Inc.", "0001373715"),
        HoldingInfo("UBER", "Uber Technologies Inc.", "0001543151"),
        HoldingInfo("ABNB", "Airbnb Inc.", "0001559720"),
        HoldingInfo("SNOW", "Snowflake Inc.", "0001640147"),
        HoldingInfo("PLTR", "Palantir Technologies Inc.", "0001321655"),
        HoldingInfo("SHOP", "Shopify Inc.", "0001594805"),
    ],
    # --- S&P 500 / SPY ---
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
    # --- Semiconductors / SOXX ---
    "SOXX": [
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AMD", "Advanced Micro Devices", "0000002488"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
        HoldingInfo("QCOM", "Qualcomm Inc.", "0000804328"),
        HoldingInfo("TXN", "Texas Instruments Inc.", "0000097476"),
        HoldingInfo("MU", "Micron Technology Inc.", "0000723125"),
        HoldingInfo("AMAT", "Applied Materials Inc.", "0000006951"),
        HoldingInfo("LRCX", "Lam Research Corp.", "0000707549"),
        HoldingInfo("KLAC", "KLA Corp.", "0000319201"),
        HoldingInfo("INTC", "Intel Corp.", "0000050863"),
        HoldingInfo("MRVL", "Marvell Technology Inc.", "0001058290"),
        HoldingInfo("ON", "ON Semiconductor Corp.", "0000861374"),
        HoldingInfo("TSM", "Taiwan Semiconductor", "0001046179"),
        HoldingInfo("ARM", "Arm Holdings plc", "0001973239"),
        HoldingInfo("ASML", "ASML Holding NV", "0000937966"),
    ],
    # --- Russell 2000 / IWM ---
    "IWM": [
        HoldingInfo("ROKU", "Roku Inc.", "0001428439"),
        HoldingInfo("ETSY", "Etsy Inc.", "0001370637"),
        HoldingInfo("DKNG", "DraftKings Inc.", "0001883685"),
        HoldingInfo("PINS", "Pinterest Inc.", "0001562088"),
        HoldingInfo("SNAP", "Snap Inc.", "0001564408"),
    ],
    # --- Technology Select / XLK ---
    "XLK": [
        HoldingInfo("AAPL", "Apple Inc.", "0000320193"),
        HoldingInfo("MSFT", "Microsoft Corp.", "0000789019"),
        HoldingInfo("NVDA", "NVIDIA Corp.", "0001045810"),
        HoldingInfo("AVGO", "Broadcom Inc.", "0001649338"),
        HoldingInfo("CRM", "Salesforce Inc.", "0001108524"),
    ],
    # --- Financial Select / XLF ---
    "XLF": [
        HoldingInfo("BRK-B", "Berkshire Hathaway Inc.", "0001067983"),
        HoldingInfo("JPM", "JPMorgan Chase & Co.", "0000019617"),
        HoldingInfo("V", "Visa Inc.", "0001403161"),
        HoldingInfo("MA", "Mastercard Inc.", "0001141391"),
        HoldingInfo("BAC", "Bank of America Corp.", "0000070858"),
        HoldingInfo("WFC", "Wells Fargo & Co.", "0000072971"),
        HoldingInfo("GS", "Goldman Sachs Group", "0000886982"),
        HoldingInfo("MS", "Morgan Stanley", "0000895421"),
        HoldingInfo("C", "Citigroup Inc.", "0000831001"),
        HoldingInfo("BLK", "BlackRock Inc.", "0001364742"),
        HoldingInfo("SCHW", "Charles Schwab Corp.", "0000316709"),
        HoldingInfo("AXP", "American Express Co.", "0000004962"),
        HoldingInfo("USB", "U.S. Bancorp", "0000036104"),
        HoldingInfo("PNC", "PNC Financial Services", "0000713676"),
        HoldingInfo("COF", "Capital One Financial", "0000927628"),
        HoldingInfo("PYPL", "PayPal Holdings Inc.", "0001633917"),
    ],
    # --- Biotech / XBI ---
    "XBI": [
        HoldingInfo("MRNA", "Moderna Inc.", "0001682852"),
        HoldingInfo("PFE", "Pfizer Inc.", "0000078003"),
        HoldingInfo("JNJ", "Johnson & Johnson", "0000200406"),
        HoldingInfo("ABBV", "AbbVie Inc.", "0001551152"),
        HoldingInfo("LLY", "Eli Lilly and Co.", "0000059478"),
        HoldingInfo("AMGN", "Amgen Inc.", "0000318154"),
        HoldingInfo("GILD", "Gilead Sciences Inc.", "0000882095"),
        HoldingInfo("BIIB", "Biogen Inc.", "0000875045"),
        HoldingInfo("REGN", "Regeneron Pharmaceuticals", "0000872589"),
        HoldingInfo("BMY", "Bristol-Myers Squibb", "0000014272"),
        HoldingInfo("UNH", "UnitedHealth Group Inc.", "0000731766"),
        HoldingInfo("TMO", "Thermo Fisher Scientific", "0000097745"),
        HoldingInfo("ABT", "Abbott Laboratories", "0000001800"),
        HoldingInfo("VRTX", "Vertex Pharmaceuticals", "0000875320"),
        HoldingInfo("ISRG", "Intuitive Surgical Inc.", "0001035267"),
    ],
    # --- Energy Select / XLE (constituents for energy sector) ---
    "XLE": [
        HoldingInfo("XOM", "Exxon Mobil Corp.", "0000034088"),
        HoldingInfo("CVX", "Chevron Corp.", "0000093410"),
        HoldingInfo("COP", "ConocoPhillips", "0001163165"),
        HoldingInfo("SLB", "Schlumberger Ltd.", "0000087347"),
        HoldingInfo("EOG", "EOG Resources Inc.", "0000821189"),
        HoldingInfo("MPC", "Marathon Petroleum Corp.", "0001510295"),
        HoldingInfo("OXY", "Occidental Petroleum", "0000797468"),
        HoldingInfo("PSX", "Phillips 66", "0001534701"),
        HoldingInfo("VLO", "Valero Energy Corp.", "0001035002"),
        HoldingInfo("HAL", "Halliburton Co.", "0000045012"),
        HoldingInfo("DVN", "Devon Energy Corp.", "0001090012"),
        HoldingInfo("FANG", "Diamondback Energy Inc.", "0001539838"),
    ],
    # --- Oil commodity ETF (no equity holdings) ---
    "USO": [],
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
