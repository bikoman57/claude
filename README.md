# Leveraged ETF Swing Trading System

Mean-reversion swing trading on leveraged ETFs, powered by Claude Code agents. Monitors underlying index drawdowns from all-time highs and signals when to enter leveraged ETFs like TQQQ, SOXL, and UPRO — notifying you on Telegram.

## Strategy

When an underlying index (e.g., Nasdaq-100) drops X% from its all-time high, that's historically a signal to buy the leveraged ETF (e.g., TQQQ at 3x). Indices tend to revert to ATH within months, and the leveraged ETF amplifies the recovery. Take profit at a conservative target (e.g., 10%).

**Signal lifecycle**: WATCH → ALERT → SIGNAL → ACTIVE → TARGET

**Confidence scoring**: Each signal is scored across 5 factors (drawdown depth, VIX regime, Fed policy, yield curve, SEC sentiment) → HIGH (4-5 favorable), MEDIUM (2-3), LOW (0-1).

## ETF Universe

| Leveraged | Underlying | Leverage | Buy When Down | Target |
|-----------|------------|----------|---------------|--------|
| TQQQ | QQQ (Nasdaq-100) | 3x | 5% | +10% |
| UPRO | SPY (S&P 500) | 3x | 5% | +10% |
| SOXL | SOXX (Semiconductors) | 3x | 8% | +10% |
| TNA | IWM (Russell 2000) | 3x | 7% | +10% |
| TECL | XLK (Tech) | 3x | 7% | +10% |
| FAS | XLF (Financials) | 3x | 7% | +10% |
| LABU | XBI (Biotech) | 3x | 10% | +10% |
| UCO | USO (Oil) | 2x | 10% | +10% |

## Quick Start

```bash
git clone https://github.com/bikoman57/claude.git
cd claude
uv sync
```

Set up Telegram (one-time): run `/telegram-setup` in Claude Code.

## Usage

### Skills (in Claude Code)

| Skill | What it does |
|---|---|
| `/unified-report` | Full orchestrated report: drawdowns + macro + SEC + confidence |
| `/analyze-etf TQQQ` | Deep analysis: drawdown + macro + SEC + momentum + confidence |
| `/scan-opportunities` | Scan all ETFs for entry/exit signals with macro context |
| `/market-report` | Quick drawdown dashboard + positions |
| `/telegram-notify "message"` | Send alert to your phone |
| `/telegram-ask "question"` | Ask you a question, wait for reply |

### CLI

```bash
# ETF analysis
uv run python -m app.etf universe        # Print ETF universe
uv run python -m app.etf scan            # Scan all underlyings for drawdowns
uv run python -m app.etf drawdown QQQ    # Check one underlying
uv run python -m app.etf stats QQQ 0.05  # Recovery stats for 5% drawdown
uv run python -m app.etf signals         # List current signals
uv run python -m app.etf active          # List active positions
uv run python -m app.etf enter TQQQ 48   # Record position entry
uv run python -m app.etf close TQQQ 53   # Close position with exit price

# Macro dashboard
uv run python -m app.macro dashboard     # VIX + CPI + GDP + unemployment
uv run python -m app.macro rates         # Fed funds rate + trajectory
uv run python -m app.macro yields        # Treasury yield curve
uv run python -m app.macro calendar      # Upcoming FOMC dates

# SEC filings
uv run python -m app.sec recent          # Recent filings for all index holdings
uv run python -m app.sec filings AAPL    # Filings for a specific ticker
uv run python -m app.sec institutional   # 13F filings from tracked institutions

# History & learning
uv run python -m app.history outcomes    # View trade outcomes
uv run python -m app.history weights     # Factor weight analysis
uv run python -m app.history summary     # Latest analysis snapshot
uv run python -m app.history snapshots   # List all snapshots
```

## Agents

| Agent | Purpose | Model |
|---|---|---|
| `chief-analyst` | Orchestrates all modules into unified report | sonnet |
| `drawdown-monitor` | ATH drawdown tracking with macro context | sonnet |
| `market-analyst` | Momentum, volatility, Fed rates, yield curve | sonnet |
| `macro-analyst` | Macro data interpretation for mean-reversion | sonnet |
| `sec-analyst` | SEC filings and institutional sentiment | sonnet |
| `swing-screener` | Entry/exit signals with confidence scoring | sonnet |
| `code-reviewer` | Code quality review | sonnet |
| `security-reviewer` | Security vulnerability audit | sonnet |
| `token-optimizer` | Token usage audit | haiku |

## Project Structure

```
.
├── CLAUDE.md                          # Agent conventions
├── .claude/
│   ├── agents/                        # Analysis agents
│   │   ├── chief-analyst.md           # Orchestrator — unified reports
│   │   ├── drawdown-monitor.md        # ATH drawdown tracking
│   │   ├── market-analyst.md          # Momentum & volatility
│   │   ├── macro-analyst.md           # Macro data interpretation
│   │   ├── sec-analyst.md             # SEC filings & institutional
│   │   ├── swing-screener.md          # Entry/exit signals
│   │   ├── code-reviewer.md           # Code review
│   │   ├── security-reviewer.md       # Security audit
│   │   └── token-optimizer.md         # Token waste audit
│   ├── skills/                        # User-facing workflows
│   │   ├── unified-report/            # /unified-report (full orchestrated)
│   │   ├── analyze-etf/               # /analyze-etf <ticker>
│   │   ├── scan-opportunities/        # /scan-opportunities
│   │   ├── market-report/             # /market-report (lite)
│   │   ├── telegram-notify/           # /telegram-notify <msg>
│   │   ├── telegram-ask/              # /telegram-ask <question>
│   │   ├── telegram-setup/            # /telegram-setup
│   │   ├── fix-issue/                 # /fix-issue <number>
│   │   ├── new-module/                # /new-module <name>
│   │   └── self-improve/              # /self-improve
│   └── settings.json                  # Permission allowlists
├── src/app/
│   ├── etf/                           # ETF analysis engine
│   │   ├── universe.py                # ETF mappings & config
│   │   ├── drawdown.py                # ATH drawdown calculation
│   │   ├── signals.py                 # Signal state machine
│   │   ├── confidence.py              # 5-factor confidence scoring
│   │   ├── store.py                   # JSON persistence
│   │   ├── stats.py                   # Recovery statistics
│   │   └── __main__.py                # CLI entry point
│   ├── macro/                         # Macro economic data
│   │   ├── indicators.py              # VIX + FRED (CPI, GDP, unemployment)
│   │   ├── fed.py                     # Fed rates, FOMC calendar, trajectory
│   │   ├── yields.py                  # Treasury yield curve (3M-30Y)
│   │   └── __main__.py                # CLI entry point
│   ├── sec/                           # SEC EDGAR integration
│   │   ├── holdings.py                # Index → top holdings mapping
│   │   ├── filings.py                 # Company filings (10-K, 10-Q, 8-K)
│   │   ├── institutional.py           # 13F institutional tracking
│   │   └── __main__.py                # CLI entry point
│   ├── history/                       # Learning & tracking
│   │   ├── recorder.py                # Analysis snapshots
│   │   ├── outcomes.py                # Trade outcome recording
│   │   ├── weights.py                 # Factor weight calculation
│   │   └── __main__.py                # CLI entry point
│   ├── telegram/                      # Telegram bot (notify + ask)
│   └── __main__.py                    # App entry point
├── tests/                             # 140 tests
├── data/                              # Runtime state (gitignored)
└── pyproject.toml                     # Dependencies & tooling
```

## Data Sources

| Source | Data | Auth |
|---|---|---|
| yfinance | Stock prices, VIX, Treasury yields | None (free) |
| FRED API | CPI, GDP, unemployment, Fed funds rate | Free API key (optional) |
| SEC EDGAR | Company filings, 13F institutional | None (User-Agent header) |

## Development

```bash
uv run pytest              # Run tests (140 tests)
uv run ruff check .        # Lint
uv run mypy src/           # Type check
```

## Disclaimer

This project is for informational and educational purposes only. It is not financial advice. Always do your own research before making investment decisions.
