# Leveraged ETF Swing Trading System

Mean-reversion swing trading on leveraged ETFs, powered by Claude Code agents. Monitors underlying index drawdowns from all-time highs and signals when to enter leveraged ETFs like TQQQ, SOXL, and UPRO — notifying you on Telegram.

## Strategy

When an underlying index (e.g., Nasdaq-100) drops X% from its all-time high, that's historically a signal to buy the leveraged ETF (e.g., TQQQ at 3x). Indices tend to revert to ATH within months, and the leveraged ETF amplifies the recovery. Take profit at a conservative target (e.g., 10%).

**Signal lifecycle**: WATCH → ALERT → SIGNAL → ACTIVE → TARGET

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
| `/analyze-etf TQQQ` | Full analysis: drawdown + momentum + recovery stats |
| `/scan-opportunities` | Scan all ETFs for entry/exit signals |
| `/market-report` | Daily drawdown dashboard + positions |
| `/telegram-notify "message"` | Send alert to your phone |
| `/telegram-ask "question"` | Ask you a question, wait for reply |

### CLI (direct)

```bash
uv run python -m app.etf universe        # Print ETF universe
uv run python -m app.etf scan            # Scan all underlyings for drawdowns
uv run python -m app.etf drawdown QQQ    # Check one underlying
uv run python -m app.etf stats QQQ 0.05  # Recovery stats for 5% drawdown
uv run python -m app.etf signals         # List current signals
uv run python -m app.etf active          # List active positions
uv run python -m app.etf enter TQQQ 48   # Record position entry
uv run python -m app.etf close TQQQ      # Close position
```

## Agents

| Agent | Purpose | Model |
|---|---|---|
| `drawdown-monitor` | ATH drawdown tracking across all underlyings | sonnet |
| `market-analyst` | Momentum, volatility regime, entry timing | sonnet |
| `swing-screener` | Entry/exit signal screening | sonnet |
| `code-reviewer` | Code quality review | sonnet |
| `security-reviewer` | Security vulnerability audit | sonnet |
| `token-optimizer` | Token usage audit | haiku |

## Project Structure

```
.
├── CLAUDE.md                          # Agent conventions
├── .claude/
│   ├── agents/                        # Analysis agents
│   │   ├── drawdown-monitor.md        # ATH drawdown tracking
│   │   ├── market-analyst.md          # Momentum & volatility
│   │   ├── swing-screener.md          # Entry/exit signals
│   │   ├── code-reviewer.md           # Code review
│   │   ├── security-reviewer.md       # Security audit
│   │   └── token-optimizer.md         # Token waste audit
│   ├── skills/                        # User-facing workflows
│   │   ├── analyze-etf/               # /analyze-etf <ticker>
│   │   ├── scan-opportunities/        # /scan-opportunities
│   │   ├── market-report/             # /market-report
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
│   │   ├── store.py                   # JSON persistence
│   │   ├── stats.py                   # Recovery statistics
│   │   └── __main__.py                # CLI entry point
│   ├── telegram/                      # Telegram bot (notify + ask)
│   └── __main__.py                    # App entry point
├── tests/                             # 49 tests
├── data/                              # Runtime signal state (gitignored)
└── pyproject.toml                     # Dependencies & tooling
```

## Development

```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run mypy src/           # Type check
```

## Disclaimer

This project is for informational and educational purposes only. It is not financial advice. Always do your own research before making investment decisions.
