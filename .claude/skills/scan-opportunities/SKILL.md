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

### Step 2: Macro + SEC Context
```bash
uv run python -m app.macro dashboard
uv run python -m app.macro yields
uv run python -m app.sec recent
```

### Step 3: Deep Dive on Signals
For any ETF in SIGNAL or ALERT state, use the `swing-screener` subagent:
> "Use the swing-screener agent to analyze entry signals from the latest scan. Focus on ETFs showing SIGNAL or ALERT states. Include confidence scores."

### Step 4: Check Active Positions
```bash
uv run python -m app.etf active
```

### Step 5: Compile Report

```
=== OPPORTUNITY SCAN ===
Date: [today]
Macro: VIX [val] [{regime}] | Fed [{trajectory}] | Yields [{curve}]

ACTION REQUIRED:
[SIGNAL] [ticker] — [underlying] down [X]% (threshold: [Y]%)
  CONFIDENCE: [HIGH/MEDIUM/LOW] ([N]/5 factors)
[TARGET] [ticker] — profit target hit, up [X]% from entry

WATCHING:
[ALERT] [ticker] — [underlying] down [X]% (threshold: [Y]%)

ACTIVE POSITIONS: [count]
[ticker]: entry $[X] → current $[Y] (P/L: [Z]%)

ALL CLEAR: [count] ETFs in normal range

This is not financial advice.
```

For the full cross-domain report, use `/unified-report` instead.

### Step 6: Telegram Alert
If there are any SIGNAL or TARGET states:
```bash
uv run python -m app.telegram notify --title "Swing Signals" "<count> actionable: <tickers>"
```
If no actionable signals, do NOT send a notification (avoid noise).

## Troubleshooting

**yfinance rate limit**: If HTTP errors occur, wait a few seconds and retry.

**Stale data on weekends**: Note in the report that markets are closed.
