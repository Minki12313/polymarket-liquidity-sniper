from loguru import logger

logger.add("logs/bot.log", rotation="5 MB", retention="7 days")
