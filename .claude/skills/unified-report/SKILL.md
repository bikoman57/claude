---
name: unified-report
description: Generate the complete unified daily swing trading report with all data sources, confidence scores, and cross-agent analysis. Use when user says "unified report", "full report", "complete report", or "daily report".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 2.0.0
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
uv run python -m app.geopolitical summary
uv run python -m app.social summary
uv run python -m app.news summary
uv run python -m app.statistics dashboard
uv run python -m app.strategy proposals
uv run python -m app.history weights
uv run python -m app.history summary
uv run python -m app.risk dashboard
uv run python -m app.portfolio dashboard
uv run python -m app.quant summary
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

### Step 3: Synthesize with CIO

Use the `exec-cio` agent to:
- Cross-reference all data sources (ETF + macro + SEC + geopolitical + social + news + statistics + strategy + risk + portfolio + quant)
- Compute confidence scores (12 factors) for each entry signal
- Apply risk-manager veto logic for portfolio limit breaches
- Identify tensions between domains (e.g., bad macro but deep drawdown, high geopolitical risk but bearish sentiment)
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
VIX: {val} [{regime}] | Fed: {trajectory} | Yields: {curve}

GEOPOLITICAL RISK
Risk Level: [HIGH/MEDIUM/LOW]
- [event summary with sector impact]

SOCIAL & OFFICIAL SENTIMENT
Reddit: [sentiment] (trending: $TICKER, $TICKER)
Officials: Fed tone [HAWKISH/DOVISH/NEUTRAL]

NEWS SENTIMENT
Overall: [sentiment] ([N] articles)
- [top headline with sector relevance]

MARKET STATISTICS
Rotation: [RISK_ON/RISK_OFF] | Put/Call: [val] | VIX Term: [structure]
Gold: $[price] ({%}) | DXY: [val] ({%})

SEC FILINGS (last 7 days)
- [ticker] [form_type] filed [date]: [materiality]

ENTRY SIGNALS
[1] BUY TQQQ — QQQ down 5.2% from ATH
    CONFIDENCE: HIGH (7/9 factors)
    Drawdown: FAV | VIX: FAV | Fed: FAV | Yields: FAV | SEC: NEU
    Geopolitical: FAV | Social: FAV | News: FAV | Stats: NEU

ACTIVE POSITIONS
| ETF  | Entry  | Current | P/L   | Target | Days |

STRATEGY INSIGHTS
- [backtest-based proposals for parameter changes]

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

**Missing Reddit credentials**: Social module will skip Reddit data. Note partial data.

**No completed trades**: Learning insights will say "No completed trades yet."
