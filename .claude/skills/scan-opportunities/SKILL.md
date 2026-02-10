---
name: scan-opportunities
description: Scan all leveraged ETFs for mean-reversion entry and exit opportunities. Use when user says "scan", "scan opportunities", "any signals", "check the market", "find entries", or "what's actionable".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Scan Opportunities

Scan all leveraged ETFs for mean-reversion opportunities. $ARGUMENTS

## Instructions

### Step 1: Run the Drawdown Scan
```bash
uv run python -m app.etf scan
```

### Step 2: Deep Dive on Signals
For any ETF in SIGNAL or ALERT state, use the `swing-screener` subagent:
> "Use the swing-screener agent to analyze entry signals from the latest scan. Focus on ETFs showing SIGNAL or ALERT states."

### Step 3: Check Active Positions
```bash
uv run python -m app.etf active
```

### Step 4: Compile Report

```
=== OPPORTUNITY SCAN ===
Date: [today]

ACTION REQUIRED:
[SIGNAL] [ticker] — [underlying] down [X]% (threshold: [Y]%)
[TARGET] [ticker] — profit target hit, up [X]% from entry

WATCHING:
[ALERT] [ticker] — [underlying] down [X]% (threshold: [Y]%)

ACTIVE POSITIONS: [count]
[ticker]: entry $[X] → current $[Y] (P/L: [Z]%)

ALL CLEAR: [count] ETFs in normal range

This is not financial advice.
```

### Step 5: Telegram Alert
If there are any SIGNAL or TARGET states:
```bash
uv run python -m app.telegram notify --title "Swing Signals" "<count> actionable: <tickers>"
```
If no actionable signals, do NOT send a notification (avoid noise).

## Troubleshooting

**yfinance rate limit**: If HTTP errors occur, wait a few seconds and retry.

**Stale data on weekends**: Note in the report that markets are closed.
