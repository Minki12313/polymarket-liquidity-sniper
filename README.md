# Polymarket Liquidity Sniper Bot

Shadow-mode Polymarket scanner with paper-trading lifecycle support.

## What it does

- Scans public Gamma markets
- Enters simulated positions when filters match
- Tracks open paper positions across restarts
- Exits on take-profit, stop-loss, or max hold time
- Writes persistent paper-trading results to disk
- Logs runtime output to `logs/bot.log`

## Runtime files

These are created automatically in the project root:

- `data/open_positions.json` — current simulated open positions
- `data/trades.csv` — closed simulated trades and realized PnL
- `logs/bot.log` — runtime log file

## Quick start

```bash
pip install -r requirements.txt
python -m src.main
```

The bot runs in a loop until stopped with `Ctrl+C`.

## Profit tracking

Realized paper-trading profit is the sum of `pnl_dollars` in `data/trades.csv`.

Each scan also prints a summary like:

- realized PnL
- number of closed trades
- win rate
- average PnL per trade
- open positions

## Important

- `live: false` keeps the bot in shadow mode.
- Live Polymarket order execution is **not implemented** in this project.
- This bot uses the public Gamma API for discovery only.
