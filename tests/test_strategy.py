from src.portfolio import Portfolio
from src.strategy import LiquiditySniperStrategy


class DummyAPI:
    def __init__(self):
        self.placed = []
        self.sold = []

    def get_markets(self):
        return [
            {
                "id": "1",
                "question": "Test market",
                "active": True,
                "closed": False,
                "archived": False,
                "liquidity": 5000,
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '[0.55, 0.45]',
            }
        ]

    def place_order(self, market_id, outcome, amount):
        self.placed.append((market_id, outcome, amount))
        return {"result": "success"}

    def sell_order(self, market_id, outcome, amount):
        self.sold.append((market_id, outcome, amount))
        return {"result": "success"}


class DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None


def test_liquidity_sniper_shadow(tmp_path):
    cfg = {
        "max_order_amount": 50,
        "live": False,
        "markets_blacklist": [],
        "min_market_liquidity": 1000,
        "min_price": 0.40,
        "max_price": 0.60,
        "take_profit_pct": 0.05,
        "stop_loss_pct": 0.03,
        "max_hold_seconds": 7200,
    }
    portfolio = Portfolio(DummyLogger(), data_dir=str(tmp_path))
    sniper = LiquiditySniperStrategy(api=DummyAPI(), config=cfg, logger=DummyLogger(), portfolio=portfolio)
    sniper.run()
    assert portfolio.has_position("1")
