class Simulator:
    def __init__(self, logger):
        self.logger = logger
        self.trades = []
    def simulate_trade(self, market_id, outcome, amount):
        msg = f"[SIM] Simulating trade on {market_id}, outcome {outcome}, amount {amount}"
        self.logger.info(msg)
        self.trades.append({
            'market_id': market_id,
            'outcome': outcome,
            'amount': amount
        })
    def get_pnl(self):
        # Placeholder: Calculate simulated profit and loss
        return 0