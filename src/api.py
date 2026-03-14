import logging
import requests


class PolymarketAPI:
    def __init__(self, api_url=None, api_key=None):
        # Gamma API for public market discovery
        self.api_url = (api_url or "https://gamma-api.polymarket.com").rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()

    def get_markets(self, limit=50, active=True, closed=False):
        url = f"{self.api_url}/markets"
        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data

            if isinstance(data, dict):
                # defensive fallback in case response shape changes
                return data.get("data", data.get("markets", []))

            logging.warning("[API] Unexpected get_markets response type: %s", type(data).__name__)
            return []

        except Exception as e:
            logging.error("[API] get_markets failed: %s", e)
            return []

    def place_order(self, market_id, outcome, amount):
        """
        Entry order stub.

        Real live trading is NOT implemented here because Polymarket trading
        uses authenticated CLOB trading flow, not a simple Gamma REST POST.
        """
        if not self.api_key:
            return {
                "status": "shadow_stub",
                "action": "buy",
                "market_id": market_id,
                "outcome": outcome,
                "amount": amount,
            }

        raise NotImplementedError(
            "Live order placement is not implemented. "
            "Polymarket trading uses the authenticated CLOB API, not a simple POST /orders."
        )

    def sell_order(self, market_id, outcome, amount):
        """
        Exit order stub.

        In shadow mode this returns a fake success payload so the rest of the
        bot can test entry/exit lifecycle cleanly.
        """
        if not self.api_key:
            return {
                "status": "shadow_stub",
                "action": "sell",
                "market_id": market_id,
                "outcome": outcome,
                "amount": amount,
            }

        raise NotImplementedError(
            "Live sell order placement is not implemented. "
            "Polymarket exits also require authenticated CLOB trading logic."
        )