---
name: screen-stocks
description: Screen a list of stocks or an index for trading signals and opportunities. Use when user says "screen stocks", "scan the market", "find signals", "what's moving", or "any opportunities".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Screen Stocks

Screen for trading signals and opportunities. $ARGUMENTS

## Instructions

### Step 1: Determine Scope
If the user specified tickers, use those. Otherwise use a default watchlist:
- **US Large Cap**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, BRK-B, JPM, V
- **User can override**: "screen INTC, AMD, QCOM" uses those instead

### Step 2: Run the Screener
Use the `signal-screener` subagent:
> "Use the signal-screener agent to scan these tickers for signals: [list]. Check for volume spikes, MA crossovers, gap moves, RSI extremes, and upcoming earnings."

### Step 3: Deep Dive on Hits
For any stock with strong signals (2+ converging signals), run a quick analysis:
> "Use the market-analyst agent to analyze [ticker] — focus on whether the signal is actionable."

### Step 4: Report
Format the results:

```
=== MARKET SCREEN ===
Date: [today]
Scanned: [count] stocks

SIGNALS FOUND:
[ranked list from signal-screener]

DEEP DIVES:
[analysis of top hits]

NO SIGNALS: [list of clean tickers]

⚠️ This is not financial advice.
```

### Step 5: Telegram Alert
If any strong signals found, notify on Telegram:
```bash
uv run python -m app.telegram notify --title "Market Screen" "<count> signals found: <tickers>"
```

If no signals, do NOT send a Telegram notification (avoid noise).

## Troubleshooting

**Too many tickers**: Screening >20 tickers at once may be slow. Split into batches of 10.

**yfinance rate limit**: If you get HTTP errors, wait 5 seconds between batches.
