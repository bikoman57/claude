---
name: team-report
description: Generate the unified daily swing trading report using PARALLEL agent teams. Faster than /unified-report — all domain analysts run simultaneously. Use when user says "team report", "parallel report", or wants faster analysis.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 3.0.0
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

Create an agent team for parallel financial analysis. Spawn **13 teammates** across 4 departments:

**Risk Management (Middle Office)**

| Teammate | Agent | Domain |
|----------|-------|--------|
| risk | risk-manager | Risk limits, exposure, VETO authority |
| portfolio | risk-portfolio | Portfolio tracking, position sizing |

**Research**

| Teammate | Agent | Domain |
|----------|-------|--------|
| macro | research-macro | VIX regime, Fed policy, yield curve, economic indicators |
| sec | research-sec | SEC filings, institutional 13F, fundamentals, earnings calendar |
| statistics | research-statistics | Sector rotation, breadth, correlations |
| strategy | research-strategy-analyst | Backtest results, parameter proposals, forecasts |
| researcher | research-strategy-researcher | New strategies, ETF candidates, market edges, research pipeline |
| quant | research-quant | Quantitative analysis, regime detection |

**Intelligence**

| Teammate | Agent | Domain |
|----------|-------|--------|
| intel-chief | intel-chief | Aggregates intel broadcasts into unified briefing |
| news | intel-news | Financial news sentiment, headlines |
| geopolitical | intel-geopolitical | Geopolitical events, sector impact |
| social | intel-social | Reddit sentiment, official statements |
| congress | intel-congress | Congressional stock trades, member ratings, prediction markets |

When spawning each teammate, include in their prompt:
1. The ETF signals from Step 1 (so they have context on what's in SIGNAL/ALERT state)
2. The current VIX level from the broad market data
3. Instructions to **broadcast key findings** when done, using this format:

```
[DOMAIN] METRIC: value (FAVORABLE/UNFAVORABLE/NEUTRAL for mean-reversion)
```

Use the Sonnet model for all teammates (except research-quant which uses opus).

### Step 3: Wait for All Teammates

Monitor teammate progress. All 13 must complete and broadcast their findings before proceeding. If a teammate stalls or errors, note the missing domain and continue with available data.

### Step 4: Synthesize Unified Report

Once all broadcasts are received, use the `exec-cio` agent logic to:

1. **Cross-reference** all domain findings — explain tensions between domains
2. **Check risk-manager for VETOs** — any vetoed signals are reported but marked as BLOCKED
3. **Include portfolio sizing** from risk-portfolio
4. **Compute confidence scores** (14 factors) for each ETF in SIGNAL state:
   - Drawdown Depth | VIX Regime | Fed Regime | Yield Curve | SEC Sentiment | Fundamentals Health
   - Prediction Markets | Earnings Risk | Geopolitical Risk | Social Sentiment | News Sentiment
   - Market Statistics | Congress Sentiment | Portfolio Risk
   - Score: **HIGH** (10+/14 favorable), **MEDIUM** (5-9), **LOW** (0-4)
5. **Flag contrarian setups**: bearish social + bearish news + deep drawdown = maximum opportunity
6. **Include learning insights** from `uv run python -m app.history weights` and `uv run python -m app.history summary`
7. **Include research ideas** from the research-strategy-researcher — new strategies, ETF candidates, market edges
8. **Include quantitative insights** from research-quant — regime, recovery stats
9. **Produce the report** in the standard unified format (see Report Format below)

### Step 5: Clean Up Team

Shut down all teammates and clean up the team.

### Step 6: Send via Telegram (optional)

```bash
uv run python -m app.telegram notify --title "Daily Swing Report" "<report summary>"
```

## Report Format

```
======================================================
       DAILY SWING TRADING REPORT -- [DATE]
       (Generated via PARALLEL AGENT TEAMS)
======================================================

MARKET OVERVIEW
Indices: SPY {%} | QQQ {%} | IWM {%}
VIX: {val} [{regime}] | Fed: {trajectory} | Yields: {curve}

RISK DASHBOARD
Portfolio: ${val} | Invested: {%} | Cash: {%}
Exposure: {%} leveraged | Positions: {N}/{max}
Risk status: [WITHIN LIMITS / WARNING / VETO ACTIVE]

INTELLIGENCE BRIEFING
Overall: [sentiment] ([confidence] confidence)
News: [sentiment] | Social: [sentiment] | Geopolitical: [risk] | Congress: [sentiment]
Prediction Markets: [overall signal] | Key: [top market + probability]
Conflicts: [any contradictions between sources]

MARKET STATISTICS
Rotation: [RISK_ON/RISK_OFF] | Put/Call: [val] | VIX Term: [structure]
Gold: $[price] ({%}) | DXY: [val] ({%})

SEC FILINGS (last 7 days)
- [ticker] [form_type] filed [date]: [materiality]
Fundamentals: [sector health classification from fundamentals-summary]
Earnings risk: [upcoming earnings within 14 days]

ENTRY SIGNALS
[1] BUY TQQQ -- QQQ down 5.2% from ATH
    CONFIDENCE: HIGH (10/14 factors)
    Drawdown: FAV | VIX: FAV | Fed: FAV | Yields: FAV | SEC: NEU | Fundamentals: FAV
    Earnings: FAV | Geopolitical: FAV | Social: FAV | News: FAV | Stats: NEU
    Congress: FAV | Risk: FAV | Prediction Markets: FAV
    Suggested position: $X (Y% of portfolio)

BLOCKED SIGNALS (risk veto)
[1] TQQQ -- BLOCKED: tech sector already 50% of portfolio

ACTIVE POSITIONS
| ETF  | Entry  | Current | P/L   | Target | Days |

STRATEGY INSIGHTS
- [backtest-based proposals for parameter changes]

FORECAST ACCURACY
Verified [N] past forecasts: [accuracy]%
Active forecasts: [list with direction and confidence]

QUANTITATIVE INSIGHTS
- Regime: [BULL/BEAR/RANGE] (confidence: X%)
- Recovery stats: [key finding]

RESEARCH IDEAS
- [new strategy proposals from research-strategy-researcher]
- [new ETF candidates with rationale]
- [market anomalies or edges discovered]

LEARNING INSIGHTS
Based on N past trades:
- Top factor: Drawdown depth (weight: 0.35)
- Win rate: X% | Avg P/L: Y%

RESEARCH STATUS
Sprint [N]: [completed]/[target] documents | In-progress: [titles]

This is not financial advice.
```

## Troubleshooting

**Agent teams not spawning**: Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is in settings.json.

**Teammate fails**: Note missing domain in report and continue. Fall back to `/unified-report` if multiple fail.

**Weekend/holiday**: Markets are closed. Note stale data in the report.

**Missing API keys**: Teammates will note partial data for their domain. Report continues.
