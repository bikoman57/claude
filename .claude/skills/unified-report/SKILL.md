---
name: unified-report
description: Generate the complete unified daily swing trading report with all data sources, confidence scores, and cross-agent analysis. Use when user says "unified report", "full report", "complete report", or "daily report".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Unified Report

Generate the complete unified swing trading report. $ARGUMENTS

## Instructions

### Step 1: Gather All Data

Run all CLI commands to collect data from every module:

```bash
uv run python -m app.etf scan
uv run python -m app.etf active
uv run python -m app.macro dashboard
uv run python -m app.macro yields
uv run python -m app.macro rates
uv run python -m app.macro calendar
uv run python -m app.sec recent
uv run python -m app.sec institutional
uv run python -m app.history weights
uv run python -m app.history summary
```

### Step 2: Broad Market Context

```bash
uv run python -c "
import yfinance as yf
for sym, name in [('SPY','S&P 500'),('QQQ','Nasdaq-100'),('IWM','Russell 2000'),('^VIX','VIX')]:
    t = yf.Ticker(sym)
    h = t.history(period='5d')
    if len(h) >= 2:
        chg = (h['Close'].iloc[-1] / h['Close'].iloc[-2] - 1) * 100
        print(f'{name}: {h[\"Close\"].iloc[-1]:.2f} ({chg:+.2f}%)')
"
```

### Step 3: Synthesize with Chief Analyst

Use the `chief-analyst` agent to:
- Cross-reference all data sources
- Compute confidence scores for each entry signal
- Identify tensions between domains (e.g., bad macro but deep drawdown)
- Produce the unified report in the format below

### Step 4: Send via Telegram

```bash
uv run python -m app.telegram notify --title "Daily Swing Report" "<report summary>"
```

## Report Format

```
══════════════════════════════════════════════════
       DAILY SWING TRADING REPORT — [DATE]
══════════════════════════════════════════════════

MARKET OVERVIEW
Indices: SPY {%} | QQQ {%} | IWM {%}
VIX: {val} [{regime}]
Fed Rate: {rate} | Next FOMC: {date} | Trajectory: {hiking/pausing/cutting}
10Y Yield: {val} | 3M-10Y Spread: {val} [{normal/inverted/flat}]

MACRO EVENTS THIS WEEK
- [upcoming events from FOMC calendar, CPI, jobs]

SEC FILINGS (last 7 days)
- [ticker] [form_type] filed [date]: [materiality]
- [institution] 13F: filed [date]

ENTRY SIGNALS
[1] BUY TQQQ — QQQ down 5.2% from ATH
    Price: $44.20 | Target: +10% ($48.62)
    Recovery: Avg 23 days, 87% success
    CONFIDENCE: HIGH (4/5 factors)
      Drawdown: FAVORABLE | VIX: FAVORABLE
      Macro: FAVORABLE | Yields: FAVORABLE | SEC: NEUTRAL

EXIT SIGNALS
[1] TAKE PROFIT UPRO — Up 10.5% from entry

ACTIVE POSITIONS
| ETF  | Entry  | Current | P/L   | Target | Days |
| SOXL | $32.50 | $34.80  | +7.1% | +10%   | 12   |

LEARNING INSIGHTS
Based on N past trades:
- Top factor: Drawdown depth (weight: 0.35)
- Win rate: X% | Avg P/L: Y%

This is not financial advice.
```

## Troubleshooting

**Weekend/holiday**: Markets are closed. Note stale data in the report.

**Missing FRED_API_KEY**: Macro dashboard will only show VIX. Note partial data.

**Missing SEC_EDGAR_EMAIL**: SEC filings will be skipped. Note in report.

**No completed trades**: Learning insights will say "No completed trades yet."
