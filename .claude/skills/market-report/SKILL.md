---
name: market-report
description: Generate a quick drawdown and position report (lite version). For the full unified report with macro, SEC, and confidence scores, use /unified-report instead. Use when user says "market report", "quick report", "drawdown report", "position report", "portfolio update", or "status".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 3.0.0
  category: financial-analysis
---

# Market Report (Lite)

Generate a quick swing trading status report. For the full unified report, use `/unified-report`. $ARGUMENTS

## Instructions

### Step 1: Full Universe Scan
```bash
uv run python -m app.etf scan
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

### Step 3: Active Positions Update
```bash
uv run python -m app.etf active
```

### Step 4: Compile Report

```
=== SWING TRADING REPORT — [date] ===

MARKET:
[index data from step 2]
VIX: [value] ([low/normal/elevated/extreme])

DRAWDOWN DASHBOARD:
| Underlying | From ATH | Threshold | Signal |
|------------|----------|-----------|--------|
| QQQ        | -3.2%    | 5%        | WATCH  |
| SOXX       | -9.1%    | 8%        | SIGNAL |
...

ACTIVE POSITIONS: [count]
| ETF  | Entry   | Current | P/L    | Target |
|------|---------|---------|--------|--------|
| SOXL | $32.50  | $34.80  | +7.1%  | +10%   |

ACTIONABLE:
- [BUY signals / TAKE PROFIT signals / No action needed]

This is not financial advice.
```

### Step 5: Send via Telegram
```bash
uv run python -m app.telegram notify --title "Daily Swing Report" "<report summary>"
```

## Note

This is the **lite** version focusing on drawdowns and positions only.
For the full report with macro dashboard, SEC filings, confidence scores,
and learning insights, use `/unified-report` instead.

## Troubleshooting

**Weekend/holiday**: Markets are closed. Note stale data in the report.

**Missing data**: Some tickers may have delayed data. Skip and note it.
