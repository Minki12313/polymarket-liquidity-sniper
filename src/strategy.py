import abc
import json
import time


class BaseStrategy(abc.ABC):
    def __init__(self, api, config, logger):
        self.api = api
        self.config = config
        self.logger = logger

    @abc.abstractmethod
    def run(self):
        pass


class LiquiditySniperStrategy(BaseStrategy):
    def __init__(self, api, config, logger, portfolio):
        super().__init__(api, config, logger)
        self.portfolio = portfolio

        self.amount_threshold = float(config.get("max_order_amount", 50))
        self.min_liquidity = float(config.get("min_market_liquidity", 1000))
        self.min_price = float(config.get("min_price", 0.40))
        self.max_price = float(config.get("max_price", 0.60))
        self.dedupe_window_seconds = int(config.get("dedupe_window_seconds", 300))

        self.take_profit_pct = float(config.get("take_profit_pct", 0.05))
        self.stop_loss_pct = float(config.get("stop_loss_pct", 0.03))
        self.max_hold_seconds = int(config.get("max_hold_seconds", 7200))

        self.last_seen_signals = {}

    def _safe_json_list(self, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

    def _to_float(self, value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _is_active_market(self, market):
        closed = market.get("closed", False)
        active = market.get("active", True)
        archived = market.get("archived", False)
        return active and not closed and not archived

    def _recently_signaled(self, market_id, side):
        key = f"{market_id}:{side}"
        now = time.time()
        last_ts = self.last_seen_signals.get(key)

        if last_ts is not None and (now - last_ts) < self.dedupe_window_seconds:
            return True

        self.last_seen_signals[key] = now
        return False

    def _extract_market_prices(self, market):
        outcomes = self._safe_json_list(market.get("outcomes", []))
        prices = self._safe_json_list(
            market.get("outcomePrices")
            or market.get("outcome_prices")
            or market.get("prices")
            or []
        )

        parsed = []
        for i, outcome_name in enumerate(outcomes):
            price = self._to_float(prices[i], 0) if i < len(prices) else 0
            parsed.append({
                "name": str(outcome_name),
                "price": price,
            })
        return parsed

    def _find_current_price_for_side(self, market, side):
        parsed = self._extract_market_prices(market)
        for outcome in parsed:
            if outcome["name"] == side:
                return outcome["price"]
        return None

    def _manage_exits(self, markets):
        now = time.time()
        market_map = {}

        for market in markets:
            if isinstance(market, dict):
                market_id = str(market.get("id") or market.get("slug") or "unknown_market")
                market_map[market_id] = market

        for pos in self.portfolio.all_positions():
            market_id = str(pos["market_id"])
            side = pos["side"]
            entry_price = float(pos["entry_price"])
            opened_at = float(pos["opened_at"])

            market = market_map.get(market_id)
            if not market:
                self.logger.warning("Open position market {} not found in latest scan", market_id)
                continue

            current_price = self._find_current_price_for_side(market, side)
            if current_price is None:
                self.logger.warning("Could not find current price for market {} side {}", market_id, side)
                continue

            tp_price = entry_price * (1 + self.take_profit_pct)
            sl_price = entry_price * (1 - self.stop_loss_pct)
            held_seconds = now - opened_at

            reason = None
            if current_price >= tp_price:
                reason = "take_profit"
            elif current_price <= sl_price:
                reason = "stop_loss"
            elif held_seconds >= self.max_hold_seconds:
                reason = "max_hold"

            if reason:
                self.logger.info(
                    "[EXIT SIGNAL] market={} side={} entry={} current={} reason={}",
                    market_id,
                    side,
                    entry_price,
                    current_price,
                    reason,
                )

                if self.config.get("live"):
                    result = self.api.sell_order(
                        market_id=market_id,
                        outcome=side,
                        amount=pos["size"],
                    )
                    self.logger.info("Exit order result: {}", result)
                else:
                    self.logger.info(
                        "Shadow mode: Simulated EXIT on market={} side={} size={} reason={}",
                        market_id,
                        side,
                        pos["size"],
                        reason,
                    )

                self.portfolio.close_position(
                    market_id=market_id,
                    exit_price=current_price,
                    reason=reason,
                )

    def run(self):
        markets = self.api.get_markets()

        if not markets:
            self.logger.error("No markets returned.")
            return

        if not isinstance(markets, list):
            self.logger.error("Expected markets to be a list, got {}", type(markets).__name__)
            return

        self.logger.info("Fetched {} markets", len(markets))

        self._manage_exits(markets)

        whitelist = self.config.get("markets_whitelist", [])
        blacklist = self.config.get("markets_blacklist", [])

        scanned = 0
        candidates = 0

        for market in markets:
            if not isinstance(market, dict):
                continue

            market_id = str(market.get("id") or market.get("slug") or "unknown_market")
            question = market.get("question") or market.get("title") or market_id

            if whitelist and market_id not in [str(x) for x in whitelist]:
                continue
            if market_id in [str(x) for x in blacklist]:
                continue
            if not self._is_active_market(market):
                continue
            if self.portfolio.has_position(market_id):
                continue

            scanned += 1

            market_liquidity = self._to_float(market.get("liquidity"), 0)
            if market_liquidity < self.min_liquidity:
                continue

            parsed = self._extract_market_prices(market)
            if not parsed:
                continue

            chosen = None
            for outcome in parsed:
                if self.min_price <= outcome["price"] <= self.max_price:
                    chosen = outcome
                    break

            if not chosen:
                continue

            if self._recently_signaled(market_id, chosen["name"]):
                continue

            candidates += 1

            self.logger.info(
                "[ENTRY SIGNAL] market={} question='{}' side={} price={} liquidity={}",
                market_id,
                question,
                chosen["name"],
                chosen["price"],
                market_liquidity,
            )

            if self.config.get("live"):
                result = self.api.place_order(
                    market_id,
                    chosen["name"],
                    self.amount_threshold,
                )
                self.logger.info("Entry order result: {}", result)
            else:
                self.logger.info(
                    "Shadow mode: Simulated ENTRY on market={} side={} size={}",
                    market_id,
                    chosen["name"],
                    self.amount_threshold,
                )

            self.portfolio.open_position(
                market_id=market_id,
                question=question,
                side=chosen["name"],
                entry_price=chosen["price"],
                size=self.amount_threshold,
            )

        self.logger.info(
            "Scan complete. scanned_active_markets={} candidates={} open_positions={}",
            scanned,
            candidates,
            len(self.portfolio.all_positions()),
        )
