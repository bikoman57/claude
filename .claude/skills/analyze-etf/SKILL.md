---
name: analyze-etf
description: Analyze a specific leveraged ETF opportunity for mean-reversion swing trading. Use when user says "analyze TQQQ", "look at SOXL", "check TQQQ", "should I enter TQQQ", or provides a leveraged ETF ticker.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Analyze ETF

Analyze the leveraged ETF opportunity for: $ARGUMENTS

## Instructions

### Step 1: Look Up the ETF
```bash
uv run python -m app.etf universe
```
Find the underlying ticker for the given leveraged ETF (or vice versa).

### Step 2: Get Drawdown Data
```bash
uv run python -m app.etf drawdown <underlying_ticker>
```

### Step 3: Get Historical Recovery Stats
```bash
uv run python -m app.etf stats <underlying_ticker> <drawdown_threshold>
```

### Step 4: Market Context
Use the `market-analyst` subagent:
> "Use the market-analyst agent to assess momentum and volatility conditions for [underlying_ticker] to determine if conditions favor a mean-reversion entry on [leveraged_ticker]."

### Step 5: Synthesize

```
=== [LEVERAGED_TICKER] ANALYSIS ===

UNDERLYING: [ticker] — down [X]% from ATH ($[ath] on [date])
SIGNAL STATE: [WATCH/ALERT/SIGNAL]
LEVERAGED ETF: [ticker] at $[price] ([X]x leverage)

RECOVERY HISTORY (from [threshold]% drawdowns):
- Episodes in last 10 years: [N]
- Avg recovery: [N] trading days (~[M] months)
- Recovery rate: [X]%

MARKET CONTEXT: [from market-analyst]

ASSESSMENT: [Is this near an entry zone? What's the risk?]
Entry price: $[X] → Target: +[Y]% ($[Z])

This is not financial advice.
```

### Step 6: Notify on Telegram
If the signal state is SIGNAL or ALERT:
```bash
uv run python -m app.telegram notify --title "[TICKER] Signal" "<summary>"
```

## Troubleshooting

**Unknown ticker**: Check `uv run python -m app.etf universe` to see supported ETFs.

**No historical data**: yfinance may not have enough history. Try adjusting the period.
