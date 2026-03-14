import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Optional


class Portfolio:
    def __init__(self, logger, data_dir: str = "data"):
        self.logger = logger
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.positions_file = self.data_dir / "open_positions.json"
        self.trades_file = self.data_dir / "trades.csv"
        self.positions: Dict[str, dict] = {}

        self._ensure_trade_log()
        self._load_positions()

    def _ensure_trade_log(self):
        if not self.trades_file.exists():
            with self.trades_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "market_id",
                        "question",
                        "side",
                        "entry_price",
                        "exit_price",
                        "size",
                        "reason",
                        "pnl_dollars",
                        "pnl_pct",
                        "held_seconds",
                    ],
                )
                writer.writeheader()

    def _load_positions(self):
        if not self.positions_file.exists():
            self.positions = {}
            return
        try:
            with self.positions_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.positions = data
            else:
                self.positions = {}
        except Exception as e:
            self.logger.warning("Failed to load positions file {}: {}", self.positions_file, e)
            self.positions = {}

    def _save_positions(self):
        with self.positions_file.open("w", encoding="utf-8") as f:
            json.dump(self.positions, f, indent=2)

    def _append_trade(self, trade_row: dict):
        with self.trades_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "market_id",
                    "question",
                    "side",
                    "entry_price",
                    "exit_price",
                    "size",
                    "reason",
                    "pnl_dollars",
                    "pnl_pct",
                    "held_seconds",
                ],
            )
            writer.writerow(trade_row)

    def has_position(self, market_id):
        return str(market_id) in self.positions

    def open_position(self, market_id, question, side, entry_price, size):
        market_id = str(market_id)
        self.positions[market_id] = {
            "market_id": market_id,
            "question": question,
            "side": side,
            "entry_price": float(entry_price),
            "size": float(size),
            "opened_at": time.time(),
        }
        self._save_positions()
        self.logger.info(
            "[POSITION OPEN] market={} side={} entry_price={} size={}",
            market_id,
            side,
            entry_price,
            size,
        )

    def close_position(self, market_id, exit_price, reason):
        market_id = str(market_id)
        pos = self.positions.get(market_id)
        if not pos:
            return None

        entry_price = float(pos["entry_price"])
        size = float(pos["size"])
        held_seconds = max(0.0, time.time() - float(pos["opened_at"]))

        if entry_price > 0:
            pnl_dollars = size * ((float(exit_price) - entry_price) / entry_price)
            pnl_pct = ((float(exit_price) - entry_price) / entry_price) * 100.0
        else:
            pnl_dollars = 0.0
            pnl_pct = 0.0

        closed = {
            **pos,
            "exit_price": float(exit_price),
            "closed_at": time.time(),
            "reason": reason,
            "pnl_dollars": pnl_dollars,
            "pnl_pct": pnl_pct,
            "held_seconds": held_seconds,
        }

        del self.positions[market_id]
        self._save_positions()
        self._append_trade(
            {
                "timestamp": int(closed["closed_at"]),
                "market_id": market_id,
                "question": pos["question"],
                "side": pos["side"],
                "entry_price": entry_price,
                "exit_price": float(exit_price),
                "size": size,
                "reason": reason,
                "pnl_dollars": round(pnl_dollars, 6),
                "pnl_pct": round(pnl_pct, 6),
                "held_seconds": round(held_seconds, 3),
            }
        )

        self.logger.info(
            "[POSITION CLOSED] market={} side={} exit_price={} reason={} pnl=${:.2f} pnl_pct={:.2f}%",
            market_id,
            pos["side"],
            exit_price,
            reason,
            pnl_dollars,
            pnl_pct,
        )

        return closed

    def get_position(self, market_id) -> Optional[dict]:
        return self.positions.get(str(market_id))

    def all_positions(self) -> List[dict]:
        return list(self.positions.values())

    def summary_stats(self) -> dict:
        closed_trades = []
        if self.trades_file.exists():
            with self.trades_file.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                closed_trades = list(reader)

        realized_pnl = sum(float(row.get("pnl_dollars", 0) or 0) for row in closed_trades)
        wins = sum(1 for row in closed_trades if float(row.get("pnl_dollars", 0) or 0) > 0)
        losses = sum(1 for row in closed_trades if float(row.get("pnl_dollars", 0) or 0) < 0)
        closed_count = len(closed_trades)
        win_rate = (wins / closed_count * 100.0) if closed_count else 0.0
        avg_pnl = (realized_pnl / closed_count) if closed_count else 0.0

        return {
            "realized_pnl": realized_pnl,
            "closed_trades": closed_count,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "open_positions": len(self.positions),
            "positions_file": str(self.positions_file),
            "trades_file": str(self.trades_file),
        }
