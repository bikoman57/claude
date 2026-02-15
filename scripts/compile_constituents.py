"""Compile all ETF constituent data into a single JSON file and generate constituents.py."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

DATA_DIR = Path("data")


def parse_ssga_excel(etf: str) -> list[tuple[str, float]]:
    """Parse holdings from SSGA Excel file."""
    import openpyxl

    path = DATA_DIR / f"{etf.lower()}_holdings.xlsx"
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    holdings = []
    for row in ws.iter_rows(min_row=6, values_only=True):
        ticker, weight = row[1], row[4]
        if ticker and weight and isinstance(weight, (int, float)):
            t = str(ticker).strip()
            if t and t != "-":
                holdings.append((t, round(float(weight), 4)))
    holdings.sort(key=lambda x: x[1], reverse=True)
    return holdings


def parse_ishares_csv(etf: str) -> list[tuple[str, float]]:
    """Parse holdings from iShares CSV file."""
    path = DATA_DIR / f"{etf.lower()}_holdings.csv"
    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    reader = csv.reader(io.StringIO("".join(lines[9:])))
    next(reader)  # skip header
    skip_tickers = {"XTSLA", "WFFUT", "IXTH6", "USD", "-"}
    holdings = []
    for row in reader:
        if len(row) >= 6 and row[0] and row[0] not in skip_tickers:
            t = row[0].strip()
            ws = row[5].strip()
            if ws and ws != "-":
                try:
                    w = float(ws)
                    if w > 0:
                        holdings.append((t, round(w, 4)))
                except ValueError:
                    pass
    holdings.sort(key=lambda x: x[1], reverse=True)
    return holdings


# QQQ data from slickcharts/Invesco (as of Feb 2026)
QQQ_DATA: list[tuple[str, float]] = [
    ("NVDA", 8.96), ("AAPL", 7.58), ("MSFT", 6.01), ("AMZN", 4.31),
    ("GOOGL", 3.86), ("GOOG", 3.61), ("META", 3.27), ("TSLA", 3.16),
    ("AVGO", 3.11), ("WMT", 2.16), ("ASML", 1.11), ("MU", 0.94),
    ("COST", 0.91), ("AMD", 0.68), ("NFLX", 0.66), ("PLTR", 0.63),
    ("CSCO", 0.62), ("LRCX", 0.60), ("AMAT", 0.57), ("TMUS", 0.49),
    ("INTC", 0.47), ("PEP", 0.46), ("LIN", 0.46), ("TXN", 0.42),
    ("AMGN", 0.40), ("GILD", 0.39), ("KLAC", 0.39), ("ISRG", 0.35),
    ("ADI", 0.33), ("HON", 0.31), ("QCOM", 0.30), ("SHOP", 0.29),
    ("PDD", 0.29), ("PANW", 0.27), ("BKNG", 0.27), ("ARM", 0.27),
    ("APP", 0.27), ("VRTX", 0.25), ("CMCSA", 0.23), ("INTU", 0.22),
    ("ADBE", 0.22), ("CRWD", 0.22), ("SBUX", 0.21), ("CEG", 0.21),
    ("MELI", 0.20), ("WDC", 0.19), ("MAR", 0.19), ("STX", 0.19),
    ("ADP", 0.17), ("REGN", 0.17), ("SNPS", 0.17), ("CDNS", 0.17),
    ("ORLY", 0.17), ("MDLZ", 0.16), ("MNST", 0.16), ("CTAS", 0.15),
    ("CSX", 0.15), ("ABNB", 0.15), ("AEP", 0.14), ("WBD", 0.14),
    ("DASH", 0.14), ("PCAR", 0.13), ("MRVL", 0.13), ("FTNT", 0.13),
    ("ROST", 0.13), ("NXPI", 0.13), ("BKR", 0.12), ("MPWR", 0.11),
    ("FAST", 0.11), ("IDXX", 0.10), ("EA", 0.10), ("ADSK", 0.10),
    ("EXC", 0.10), ("XEL", 0.10), ("FANG", 0.10), ("CCEP", 0.09),
    ("MSTR", 0.09), ("DDOG", 0.09), ("MCHP", 0.09), ("ALNY", 0.09),
    ("ODFL", 0.08), ("KDP", 0.08), ("TRI", 0.08), ("WDAY", 0.07),
    ("PYPL", 0.07), ("GEHC", 0.07), ("CPRT", 0.07), ("TTWO", 0.07),
    ("ROP", 0.07), ("AXON", 0.07), ("PAYX", 0.07), ("CTSH", 0.07),
    ("INSM", 0.07), ("CHTR", 0.06), ("KHC", 0.06), ("ZS", 0.06),
    ("DXCM", 0.05), ("VRSK", 0.05), ("TEAM", 0.05), ("CSGP", 0.04),
    ("ON", 0.04), ("CDW", 0.04), ("SMCI", 0.04),
]


def main() -> None:
    all_data: dict[str, list[tuple[str, float]]] = {}

    # SSGA ETFs
    for etf in ("SPY", "XLK", "XLF", "XBI"):
        all_data[etf] = parse_ssga_excel(etf)

    # iShares ETFs
    for etf in ("SOXX", "IWM"):
        all_data[etf] = parse_ishares_csv(etf)

    # QQQ from manual data
    all_data["QQQ"] = QQQ_DATA

    # Save JSON
    json_path = DATA_DIR / "all_constituents.json"
    serializable = {k: [[t, w] for t, w in v] for k, v in all_data.items()}
    with open(json_path, "w") as f:
        json.dump(serializable, f, indent=2)

    # Print summary
    for etf, holdings in all_data.items():
        total = sum(w for _, w in holdings)
        print(f"{etf}: {len(holdings)} stocks, total: {total:.2f}%")  # noqa: T201

    # Generate constituents.py
    generate_constituents_module(all_data)


def generate_constituents_module(
    all_data: dict[str, list[tuple[str, float]]],
) -> None:
    """Generate src/app/etf/constituents.py from parsed data."""
    lines = [
        '"""ETF constituent holdings with weights.',
        "",
        "Auto-generated from official ETF provider data (SSGA, iShares, Invesco).",
        "Data as of: Feb 12, 2026.",
        "",
        "To refresh: uv run python scripts/compile_constituents.py",
        '"""',
        "from __future__ import annotations",
        "",
        "",
        "# (ticker, weight%) tuples sorted by weight descending.",
        "# Sources: SSGA (SPY, XLK, XLF, XBI), iShares (SOXX, IWM), Invesco (QQQ).",
        "# USO tracks crude oil futures — no equity constituents.",
        "",
    ]

    order = ["QQQ", "SPY", "SOXX", "IWM", "XLK", "XLF", "XBI"]
    for etf in order:
        holdings = all_data[etf]
        total = sum(w for _, w in holdings)
        lines.append(f"# {etf}: {len(holdings)} holdings, ~{total:.1f}% coverage")
        lines.append(f"{etf}_HOLDINGS: list[tuple[str, float]] = [")
        for ticker, weight in holdings:
            lines.append(f'    ("{ticker}", {weight}),')
        lines.append("]")
        lines.append("")

    # Add the lookup dict
    lines.append("")
    lines.append("# Map underlying ETF ticker -> constituent holdings")
    lines.append("CONSTITUENTS: dict[str, list[tuple[str, float]]] = {")
    for etf in order:
        lines.append(f'    "{etf}": {etf}_HOLDINGS,')
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def get_constituents(underlying_ticker: str) -> list[tuple[str, float]]:")
    lines.append('    """Return constituent (ticker, weight%) pairs for an underlying ETF."""')
    lines.append("    return CONSTITUENTS.get(underlying_ticker.upper(), [])")
    lines.append("")
    lines.append("")
    lines.append("def get_all_constituent_tickers() -> set[str]:")
    lines.append('    """Return the set of all unique constituent tickers across all ETFs."""')
    lines.append("    tickers: set[str] = set()")
    lines.append("    for holdings in CONSTITUENTS.values():")
    lines.append("        for ticker, _ in holdings:")
    lines.append("            tickers.add(ticker)")
    lines.append("    return tickers")
    lines.append("")

    out_path = Path("src/app/etf/constituents.py")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nGenerated {out_path} ({len(lines)} lines)")  # noqa: T201


if __name__ == "__main__":
    main()
