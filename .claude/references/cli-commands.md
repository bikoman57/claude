# CLI Commands Reference

## ETF Module
- `uv run python -m app.etf scan|drawdown|signals|active|stats|universe|enter|close`

## Macro Module
- `uv run python -m app.macro dashboard|rates|yields|calendar`

## SEC Module
- `uv run python -m app.sec filings|institutional|recent|earnings|earnings-calendar|earnings-summary`

## Risk Module
- `uv run python -m app.risk dashboard|check|limits`

## Portfolio Module
- `uv run python -m app.portfolio dashboard|allocations|sizing|history`

## Quantitative Module
- `uv run python -m app.quant regime|recovery-stats|factor-test|summary`

## History Module
- `uv run python -m app.history outcomes|weights|summary|snapshots`

## News Module
- `uv run python -m app.news headlines|summary|journalists`

## Geopolitical Module
- `uv run python -m app.geopolitical events|headlines|summary`

## Social Module
- `uv run python -m app.social reddit|officials|summary`

## Statistics Module
- `uv run python -m app.statistics sectors|breadth|risk|correlations|dashboard`

## Strategy Module
- `uv run python -m app.strategy backtest|optimize|proposals|compare|history`

## Congress Module
- `uv run python -m app.congress trades|members|sectors|summary`

## Polymarket Module
- `uv run python -m app.polymarket markets|summary`

## Scheduler Module
- `uv run python -m app.scheduler daily|test-run|publish|pre-market|post-market|status|ceremonies`

## Agile Module
- `uv run python -m app.agile sprint|standup|planning|review|retro|roadmap|init|advance|tasks`

## FinOps Module
- `uv run python -m app.finops dashboard|today|budget|allocate|roi|agent <name>|init`

## DevOps Module
- `uv run python -m app.devops health|pipeline|trends`

## Telegram
- `uv run python -m app.telegram notify "message"` — send notification
- `uv run python -m app.telegram ask "question"` — ask and wait for reply
- `uv run python -m app.telegram setup-check` — verify configuration
- `uv run python -m app.telegram listen` — start long-polling listener
