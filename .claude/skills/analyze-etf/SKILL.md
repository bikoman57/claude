---
name: analyze-etf
description: Analyze a specific leveraged ETF opportunity for mean-reversion swing trading. Use when user says "analyze TQQQ", "look at SOXL", "check TQQQ", "should I enter TQQQ", or provides a leveraged ETF ticker.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 2.0.0
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

### Step 4: Macro + Yield Context
```bash
uv run python -m app.macro dashboard
uv run python -m app.macro yields
uv run python -m app.macro rates
```

### Step 5: SEC Filings Context
```bash
uv run python -m app.sec recent
```

### Step 5b: Fundamentals & Earnings Risk
```bash
uv run python -m app.sec fundamentals <underlying_ticker>
uv run python -m app.sec earnings <underlying_ticker>
```

### Step 5c: Congressional Trades & Prediction Markets
```bash
uv run python -m app.congress trades --ticker <underlying_ticker>
uv run python -m app.polymarket markets
```

### Step 5d: Strategy Comparison
```bash
uv run python -m app.strategy compare <underlying_ticker>
uv run python -m app.strategy forecast
```

### Step 6: Market Momentum
Use the `trading-market-analyst` subagent:
> "Use the trading-market-analyst agent to assess momentum and volatility conditions for [underlying_ticker] to determine if conditions favor a mean-reversion entry on [leveraged_ticker]."

### Step 7: Synthesize with Confidence Score

Assess 9 factors: drawdown depth, VIX regime, Fed regime, yield curve, SEC sentiment, earnings proximity, fundamentals health, congress sentiment, prediction markets.
Score: HIGH (7-9 favorable), MEDIUM (4-6), LOW (0-3).

```
=== [LEVERAGED_TICKER] ANALYSIS ===

UNDERLYING: [ticker] — down [X]% from ATH ($[ath] on [date])
SIGNAL STATE: [WATCH/ALERT/SIGNAL]
LEVERAGED ETF: [ticker] at $[price] ([X]x leverage)

RECOVERY HISTORY (from [threshold]% drawdowns):
- Episodes in last 10 years: [N]
- Avg recovery: [N] trading days (~[M] months)
- Recovery rate: [X]%

MACRO: VIX [val] [{regime}] | Fed [{trajectory}] | Yields [{curve}]
SEC: [material filings summary or "No material filings"]
FUNDAMENTALS: [sector health — STRONG/NEUTRAL/WEAK]
EARNINGS: [next earnings date] ([RISK if within 14 days / CLEAR])
CONGRESS: [net flow for this sector — BUYING/SELLING/NEUTRAL]
PREDICTION MARKETS: [relevant market + probability or "N/A"]

STRATEGY: Best strategy [type] at [threshold]%/[target]% (Sharpe: [val], Win: [%])
FORECAST: [active forecast direction + confidence or "None"]

CONFIDENCE: [HIGH/MEDIUM/LOW] ([N]/9 factors)
  Drawdown: [FAV/UNF/NEU] | VIX: [FAV/UNF/NEU] | Fed: [FAV/UNF/NEU]
  Yields: [FAV/UNF/NEU] | SEC: [FAV/UNF/NEU] | Earnings: [FAV/UNF/NEU]
  Fundamentals: [FAV/UNF/NEU] | Congress: [FAV/UNF/NEU] | Prediction Mkts: [FAV/UNF/NEU]

ASSESSMENT: [Is this near an entry zone? What's the risk?]
Entry price: $[X] → Target: +[Y]% ($[Z])

This is not financial advice.
```

### Step 8: Notify on Telegram
If the signal state is SIGNAL or ALERT:
```bash
uv run python -m app.telegram notify --title "[TICKER] Signal" "<summary>"
```

## Troubleshooting

**Unknown ticker**: Check `uv run python -m app.etf universe` to see supported ETFs.

**No historical data**: yfinance may not have enough history. Try adjusting the period.
