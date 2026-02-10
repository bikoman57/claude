---
name: market-report
description: Generate a daily or weekly market summary report with key movers and trends. Use when user says "market report", "market summary", "what happened today", "daily recap", or "weekly review".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Market Report

Generate a market summary report. $ARGUMENTS

## Instructions

### Step 1: Fetch Index Data
Get major index performance:
```bash
uv run python -c "
import yfinance as yf
for sym, name in [('SPY','S&P 500'),('QQQ','Nasdaq 100'),('DIA','Dow 30'),('IWM','Russell 2000'),('VIX','VIX')]:
    t = yf.Ticker(sym)
    h = t.history(period='5d')
    if len(h) >= 2:
        chg = (h['Close'].iloc[-1] / h['Close'].iloc[-2] - 1) * 100
        print(f'{name} ({sym}): {h[\"Close\"].iloc[-1]:.2f} ({chg:+.2f}%)')
"
```

### Step 2: Sector Performance
Check sector ETFs for rotation:
```bash
uv run python -c "
import yfinance as yf
sectors = {'XLK':'Tech','XLF':'Financials','XLV':'Healthcare','XLE':'Energy','XLI':'Industrials','XLC':'Comms','XLY':'Consumer Disc','XLP':'Consumer Staples','XLRE':'Real Estate','XLU':'Utilities','XLB':'Materials'}
for sym, name in sectors.items():
    t = yf.Ticker(sym)
    h = t.history(period='5d')
    if len(h) >= 2:
        chg = (h['Close'].iloc[-1] / h['Close'].iloc[-2] - 1) * 100
        print(f'{name}: {chg:+.2f}%')
"
```

### Step 3: Run Signal Screen
Use the `signal-screener` agent on major stocks to find notable movers.

### Step 4: Compile Report

```
=== MARKET REPORT — [date] ===

INDICES:
[index data from step 1]

SECTOR ROTATION:
Leaders: [top 3 sectors]
Laggards: [bottom 3 sectors]

NOTABLE MOVERS:
[signals/movers from step 3]

MARKET MOOD: [risk-on/risk-off/mixed] — [1-sentence reason based on VIX, breadth, sector rotation]

⚠️ This is not financial advice.
```

### Step 5: Send via Telegram
```bash
uv run python -m app.telegram notify --title "Market Report" "<report summary>"
```

## Troubleshooting

**Weekend/holiday**: Markets are closed on weekends and holidays. yfinance will return stale data. Note this in the report.

**Missing sector data**: Some sector ETFs may have delayed data. Skip any that fail and note it.
