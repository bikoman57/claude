---
name: analyze-stock
description: Run a full analysis on a stock ticker covering price action, fundamentals, and signals. Use when user says "analyze AAPL", "what do you think about TSLA", "look at this stock", or provides a ticker symbol.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Analyze Stock

Run a comprehensive analysis on: $ARGUMENTS

## Instructions

### Step 1: Technical Analysis
Use the `market-analyst` subagent to analyze price action and technicals:
> "Use the market-analyst agent to analyze $ARGUMENTS — price trends, moving averages, RSI, support/resistance, and volume."

### Step 2: Fundamental Analysis
Use the `fundamentals-analyst` subagent to analyze financials and valuation:
> "Use the fundamentals-analyst agent to analyze $ARGUMENTS — P/E, growth, margins, debt, and valuation vs peers."

### Step 3: Signal Check
Use the `signal-screener` subagent to check for active signals:
> "Use the signal-screener agent to check $ARGUMENTS for any active trading signals — volume spikes, MA crossovers, RSI extremes, upcoming earnings."

Run steps 1-3 in parallel using subagents to save time.

### Step 4: Synthesize
Combine findings from all three agents into a single summary:

```
=== $ARGUMENTS ANALYSIS ===

TECHNICAL: [bullish/bearish/neutral] — [key reason]
FUNDAMENTAL: [undervalued/fair/overvalued] — [key reason]
SIGNALS: [active signals or "none"]

BOTTOM LINE: [2-3 sentences combining all perspectives]

⚠️ This is not financial advice. Do your own research.
```

### Step 5: Notify on Telegram
Send the summary to Telegram:
```bash
uv run python -m app.telegram notify --title "$ARGUMENTS Analysis" "<summary>"
```

## Troubleshooting

**yfinance returns no data**: The ticker may be invalid or delisted. Try verifying with `uv run python -c "import yfinance as yf; print(yf.Ticker('$ARGUMENTS').info.get('shortName'))"`.

**Subagent timeout**: If a subagent takes too long, it may be fetching too much data. Narrow the analysis period.
