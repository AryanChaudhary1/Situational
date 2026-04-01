"""Alpaca paper trading client — one-click execution of thesis recommendations."""
from __future__ import annotations
from dataclasses import dataclass
import logging

from backend.config import Config

logger = logging.getLogger(__name__)
from backend.engine.causal_engine import InvestmentThesis


@dataclass
class OrderResult:
    ticker: str
    direction: str
    shares: int
    order_type: str
    status: str
    message: str


class AlpacaTrader:
    def __init__(self, config: Config):
        self.config = config
        self.client = None

        if config.alpaca_api_key and config.alpaca_secret_key:
            try:
                from alpaca.trading.client import TradingClient
                self.client = TradingClient(
                    config.alpaca_api_key,
                    config.alpaca_secret_key,
                    paper=True,
                )
            except Exception as e:
                logger.warning("Alpaca init error: %s", e)

    def is_configured(self) -> bool:
        return self.client is not None

    def get_account_info(self) -> dict:
        if not self.client:
            return {"error": "Alpaca not configured"}
        try:
            account = self.client.get_account()
            return {
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_positions(self) -> list[dict]:
        if not self.client:
            return []
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    "ticker": p.symbol,
                    "qty": float(p.qty),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                }
                for p in positions
            ]
        except Exception as e:
            logger.warning("Position fetch error: %s", e)
            return []

    def execute_thesis(self, thesis: InvestmentThesis, portfolio_value: float | None = None) -> list[OrderResult]:
        """Execute all recommendations from a thesis via paper trading."""
        if not self.client:
            return [OrderResult("N/A", "N/A", 0, "N/A", "error", "Alpaca not configured")]

        if portfolio_value is None:
            try:
                account = self.client.get_account()
                portfolio_value = float(account.portfolio_value)
            except Exception:
                portfolio_value = self.config.portfolio_size

        results = []
        for rec in thesis.tickers:
            try:
                # Calculate share count from position size
                position_value = portfolio_value * rec.position_size_pct
                price = rec.current_price if rec.current_price > 0 else 1
                shares = int(position_value / price)

                if shares <= 0:
                    results.append(OrderResult(
                        rec.ticker, rec.direction, 0, "skip",
                        "skipped", f"Position too small ({position_value:.0f})",
                    ))
                    continue

                from alpaca.trading.requests import MarketOrderRequest
                from alpaca.trading.enums import OrderSide, TimeInForce

                side = OrderSide.BUY if rec.direction == "LONG" else OrderSide.SELL
                order_data = MarketOrderRequest(
                    symbol=rec.ticker,
                    qty=shares,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                )

                order = self.client.submit_order(order_data)
                results.append(OrderResult(
                    rec.ticker, rec.direction, shares, "market",
                    str(order.status), f"Order submitted: {shares} shares",
                ))

            except Exception as e:
                results.append(OrderResult(
                    rec.ticker, rec.direction, 0, "error",
                    "failed", str(e),
                ))

        return results
