---
name: team-report
description: Generate the unified daily swing trading report using PARALLEL agent teams. Faster than /unified-report — all domain analysts run simultaneously. Use when user says "team report", "parallel report", or wants faster analysis.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
  experimental: true
---

# Team Report

Generate the unified swing trading report using parallel agent teams. $ARGUMENTS

## Prerequisites

Agent teams must be enabled: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json.

## Instructions

### Step 1: Gather ETF Signals (lead runs these — fast, needed by all teammates)

```bash
uv run python -m app.etf scan
uv run python -m app.etf active
```

Also get broad market context:

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

### Step 2: Create Agent Team

Create an agent team for parallel financial analysis. Spawn **8 teammates** — one per domain:

| Teammate | Agent | Domain |
|----------|-------|--------|
| macro | macro-analyst | VIX regime, Fed policy, yield curve, economic indicators |
| sec | sec-analyst | SEC filings, institutional 13F activity |
| news | news-analyst | Financial news sentiment, headlines |
| geopolitical | geopolitical-analyst | Geopolitical events, sector impact |
| social | social-analyst | Reddit sentiment, official statements |
| statistics | statistics-analyst | Sector rotation, breadth, correlations |
| strategy | strategy-analyst | Backtest results, parameter proposals |
| researcher | strategy-researcher | New strategies, ETF candidates, market edges |

When spawning each teammate, include in their prompt:
1. The ETF signals from Step 1 (so they have context on what's in SIGNAL/ALERT state)
2. The current VIX level from the broad market data
3. Instructions to **broadcast key findings** when done, using this format:

```
[DOMAIN] METRIC: value (FAVORABLE/UNFAVORABLE/NEUTRAL for mean-reversion)
```

Use the Sonnet model for all teammates.

### Step 3: Wait for All Teammates

Monitor teammate progress. All 8 must complete and broadcast their findings before proceeding. If a teammate stalls or errors, note the missing domain and continue with available data.

### Step 4: Synthesize Unified Report

Once all broadcasts are received, use the `chief-analyst` agent logic to:

1. **Cross-reference** all domain findings — explain tensions between domains
2. **Compute confidence scores** (9 factors) for each ETF in SIGNAL state:
   - Drawdown Depth | VIX Regime | Fed Regime | Yield Curve | SEC Sentiment
   - Geopolitical Risk | Social Sentiment | News Sentiment | Market Statistics
   - Score: **HIGH** (7+/9 favorable), **MEDIUM** (4-6), **LOW** (0-3)
3. **Flag contrarian setups**: bearish social + bearish news + deep drawdown = maximum opportunity
4. **Include learning insights** from `uv run python -m app.history weights` and `uv run python -m app.history summary`
5. **Include research ideas** from the strategy-researcher — new strategies, ETF candidates, market edges
6. **Produce the report** in the standard unified format (see Report Format below)

### Step 5: Clean Up Team

Shut down all teammates and clean up the team.

### Step 6: Send via Telegram (optional)

```bash
uv run python -m app.telegram notify --title "Daily Swing Report" "<report summary>"
```

## Report Format

```
══════════════════════════════════════════════════
       DAILY SWING TRADING REPORT — [DATE]
       (Generated via PARALLEL AGENT TEAMS)
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

RESEARCH IDEAS
- [new strategy proposals from strategy-researcher]
- [new ETF candidates with rationale]
- [market anomalies or edges discovered]

LEARNING INSIGHTS
Based on N past trades:
- Top factor: Drawdown depth (weight: 0.35)
- Win rate: X% | Avg P/L: Y%

This is not financial advice.
```

## Troubleshooting

**Agent teams not spawning**: Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is in settings.json.

**Teammate fails**: Note missing domain in report and continue. Fall back to `/unified-report` if multiple fail.

**Weekend/holiday**: Markets are closed. Note stale data in the report.

**Missing API keys**: Teammates will note partial data for their domain. Report continues.
