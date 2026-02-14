---
name: macro-check
description: Quick macro environment check — VIX regime, Fed policy, yield curve, regime detection, risk indicators, and sector rotation. Use when user says "macro check", "macro dashboard", "how's the economy", "what's the Fed doing", "yield curve", "VIX regime", "rates check".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Macro Check

Quick macro environment assessment for mean-reversion context. $ARGUMENTS

## Instructions

### Step 1: Gather Macro Data

Run all macro and related CLIs:

```bash
uv run python -m app.macro dashboard
uv run python -m app.macro yields
uv run python -m app.macro rates
uv run python -m app.macro calendar
uv run python -m app.statistics risk
uv run python -m app.statistics sectors
uv run python -m app.quant regime
```

### Step 2: Broad Market Prices

```bash
uv run python -c "
import yfinance as yf
for sym, name in [('SPY','S&P 500'),('QQQ','Nasdaq-100'),('IWM','Russell 2000'),('^VIX','VIX'),('^TNX','10Y Yield')]:
    t = yf.Ticker(sym)
    h = t.history(period='5d')
    if len(h) >= 2:
        chg = (h['Close'].iloc[-1] / h['Close'].iloc[-2] - 1) * 100
        print(f'{name}: {h[\"Close\"].iloc[-1]:.2f} ({chg:+.2f}%)')
"
```

### Step 3: Compile Report

No agent needed — synthesize the data directly:

```
=== MACRO ENVIRONMENT -- [DATE] ===

MARKET: SPY [%] | QQQ [%] | IWM [%]
VIX: [val] ([LOW/ELEVATED/HIGH/EXTREME]) | 10Y: [val]%

FED POLICY:
Rate: [current]% | Trajectory: [HIKING/CUTTING/HOLDING]
Next FOMC: [date] ([N] days away)
Global: ECB [rate]% | BoE [rate]% | BoJ [rate]%

YIELD CURVE:
2Y/10Y spread: [bps] ([INVERTED/NORMAL/FLAT])
Assessment: [impact on mean-reversion strategy]

REGIME: [BULL/BEAR/RANGE] (confidence: [X]%)
60d return: [%] | Annualized vol: [%]

RISK INDICATORS:
Gold: $[price] ([%]) | Oil: $[price] ([%]) | DXY: [val] ([%])
Put/Call: [val] | Assessment: [RISK_ON/RISK_OFF]

SECTOR ROTATION: [signal]
Leaders: [sectors] | Laggards: [sectors]

MACRO ASSESSMENT FOR MEAN-REVERSION:
[FAVORABLE/UNFAVORABLE/NEUTRAL] -- [brief explanation of why]

This is not financial advice.
```

No Telegram notification (this is a quick check, not an alert).

## Troubleshooting

**Missing FRED_API_KEY**: Macro dashboard will only show VIX. Note partial data.

**yfinance rate limit**: If HTTP errors occur, wait a few seconds and retry.

**Weekend/holiday**: Markets are closed. Note stale data.
