import time
from pathlib import Path

import yaml
from loguru import logger

from src.api import PolymarketAPI
from src.portfolio import Portfolio
from src.strategy import LiquiditySniperStrategy


def ensure_runtime_dirs():
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)


def configure_logger(log_level: str = "INFO"):
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)
    logger.add(
        "logs/bot.log",
        level=log_level,
        rotation="5 MB",
        retention="7 days",
        enqueue=False,
    )


def load_config():
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_bot():
    ensure_runtime_dirs()
    config = load_config() or {}
    configure_logger(config.get("log_level", "INFO"))

    api = PolymarketAPI(
        api_url=config.get("api_url"),
        api_key=config.get("api_key"),
    )

    portfolio = Portfolio(logger, data_dir=config.get("data_dir", "data"))
    strategy = LiquiditySniperStrategy(
        api=api,
        config=config,
        logger=logger,
        portfolio=portfolio,
    )

    poll_interval = int(config.get("poll_interval_seconds", 15))

    if config.get("live"):
        logger.warning("Running in LIVE MODE. Real trades may be placed.")
    else:
        logger.info("Running in SHADOW (simulation) MODE. No real trades will be placed.")

    while True:
        try:
            strategy.run()
            stats = portfolio.summary_stats()
            logger.info(
                "[STATS] realized_pnl=${:.2f} closed_trades={} win_rate={:.1f}% avg_pnl=${:.2f} open_positions={} trades_file={}",
                stats["realized_pnl"],
                stats["closed_trades"],
                stats["win_rate"],
                stats["avg_pnl"],
                stats["open_positions"],
                stats["trades_file"],
            )
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.exception("Bot error: {}", e)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
