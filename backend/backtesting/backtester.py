"""Backtester — prediction logger + scoring engine. This is the moat.

Every thesis the agent generates gets logged with specific entry/target/stop levels.
Daily, we check all open predictions against current prices and resolve them.
Over time, this builds a track record that:
1. Proves (or disproves) the agent's edge
2. Feeds back into the agent to improve thesis quality
3. Gives users confidence in the recommendations

Resolution logic:
- Hit target price → WIN
- Hit stop loss → LOSS
- Time horizon expired → evaluate at expiry
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.db.database import (
    save_prediction, get_open_predictions, resolve_prediction, get_all_predictions,
)
from backend.engine.ticker_validator import get_current_price
from backend.engine.causal_engine import InvestmentThesis
from backend.constants import (
    DEFAULT_TARGET_MULTIPLIER,
    DEFAULT_STOP_MULTIPLIER,
    PRICE_RATIO_MIN,
    PRICE_RATIO_MAX,
    RISK_FREE_RATE_ANNUAL,
    TRADING_DAYS_PER_YEAR,
)

logger = logging.getLogger(__name__)


@dataclass
class TrackRecord:
    total_predictions: int
    resolved: int
    open: int
    wins: int
    losses: int
    expired: int
    win_rate: float  # 0.0-1.0
    avg_return_pct: float
    best_trade: str
    worst_trade: str
    avg_confidence: float
    sharpe_estimate: float  # rough Sharpe approximation

    def to_dict(self) -> dict:
        return {
            "total_predictions": self.total_predictions,
            "resolved": self.resolved,
            "open": self.open,
            "wins": self.wins,
            "losses": self.losses,
            "expired": self.expired,
            "win_rate": round(self.win_rate * 100, 1),
            "avg_return_pct": round(self.avg_return_pct, 2),
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "avg_confidence": round(self.avg_confidence, 2),
            "sharpe_estimate": round(self.sharpe_estimate, 2),
        }

    def to_summary(self) -> str:
        return (
            f"=== TRACK RECORD ===\n"
            f"Total: {self.total_predictions} | Open: {self.open} | "
            f"Resolved: {self.resolved}\n"
            f"Wins: {self.wins} | Losses: {self.losses} | Expired: {self.expired}\n"
            f"Win Rate: {self.win_rate*100:.1f}%\n"
            f"Avg Return: {self.avg_return_pct:+.2f}%\n"
            f"Sharpe Estimate: {self.sharpe_estimate:.2f}\n"
            f"Best: {self.best_trade}\n"
            f"Worst: {self.worst_trade}\n"
        )


def _parse_price(price_str: str) -> float | None:
    """Extract a number from a price string like '$440-445' or '$460'."""
    if not price_str:
        return None
    numbers = re.findall(r'[\d.]+', str(price_str))
    if not numbers:
        return None
    # If range (e.g., '$440-445'), take midpoint
    if len(numbers) >= 2:
        return (float(numbers[0]) + float(numbers[1])) / 2
    return float(numbers[0])


class Backtester:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def log_theses(self, theses: list[InvestmentThesis]):
        """Log all predictions from a list of theses with detailed validation logging."""
        for thesis in theses:
            logger.debug(f"[THESIS] {thesis.title} (confidence={thesis.confidence:.2f})")

            for rec in thesis.tickers:
                # Log raw strings before parsing
                logger.debug(f"  [{rec.ticker} {rec.direction}] Raw: entry_zone='{rec.entry_zone}' target='{rec.target}' stop='{rec.stop_loss}'")

                # Parse prices
                entry = _parse_price(rec.entry_zone)
                target = _parse_price(rec.target)
                stop = _parse_price(rec.stop_loss)

                logger.debug(f"    Parsed: entry={entry} target={target} stop={stop}")

                if not entry:
                    entry = rec.current_price if rec.current_price > 0 else 0
                    logger.debug(f"    Fallback entry: {entry} (from current_price)")

                # Apply defaults if target/stop missing
                target_final = target or entry * DEFAULT_TARGET_MULTIPLIER
                stop_final = stop or entry * DEFAULT_STOP_MULTIPLIER

                if not target:
                    logger.warning(f"    [WARN] {rec.ticker} has missing target price, using default +10%: {target_final:.2f}")
                if not stop:
                    logger.warning(f"    [WARN] {rec.ticker} has missing stop price, using default -5%: {stop_final:.2f}")

                if entry and entry > 0:
                    # Sanity check: entry price must be in the same ballpark as current price
                    # Filters out option premiums ($3.50) being mixed with stock prices ($127)
                    current = rec.current_price
                    if current > 0:
                        ratio = entry / current
                        if ratio < PRICE_RATIO_MIN or ratio > PRICE_RATIO_MAX:
                            logger.warning(
                                f"    [SKIP] {rec.ticker} entry ${entry:.2f} is {ratio:.1f}x current "
                                f"${current:.2f} — likely option/stock price mismatch, skipping"
                            )
                            continue

                    # Validate price logic for direction
                    if rec.direction == "LONG" and target_final <= entry:
                        logger.error(f"    [ERROR] {rec.ticker} LONG but target ({target_final:.2f}) <= entry ({entry:.2f})")
                        continue
                    elif rec.direction == "SHORT" and target_final >= entry:
                        logger.error(f"    [ERROR] {rec.ticker} SHORT but target ({target_final:.2f}) >= entry ({entry:.2f})")
                        continue

                    logger.info(f"    LOGGED: {rec.ticker} {rec.direction} | entry={entry:.2f} target={target_final:.2f} stop={stop_final:.2f} conf={thesis.confidence:.2f}")

                    save_prediction(
                        db_path=self.db_path,
                        thesis_id=thesis.thesis_id,
                        ticker=rec.ticker,
                        direction=rec.direction,
                        entry_price=entry,
                        target_price=target_final,
                        stop_price=stop_final,
                        confidence=thesis.confidence,
                        thesis_summary=thesis.title,
                        time_horizon_days=thesis.time_horizon_days,
                    )
                else:
                    logger.error(f"    [SKIP] {rec.ticker} has invalid entry price: {entry}")

    def check_outcomes(self) -> list[dict]:
        """Check all open predictions against current prices. Resolve where appropriate."""
        open_preds = get_open_predictions(self.db_path)
        resolved = []

        for pred in open_preds:
            ticker = pred["ticker"]
            current_price = get_current_price(ticker)
            if current_price is None:
                continue

            entry = pred["entry_price"]
            target = pred["target_price"]
            stop = pred["stop_price"]
            direction = pred["direction"]

            if entry <= 0:
                continue

            # Calculate return based on direction
            if direction == "LONG":
                ret_pct = (current_price - entry) / entry * 100
                hit_target = current_price >= target if target else False
                hit_stop = current_price <= stop if stop else False
            else:  # SHORT
                ret_pct = (entry - current_price) / entry * 100
                hit_target = current_price <= target if target else False
                hit_stop = current_price >= stop if stop else False

            # Check time expiry
            created = datetime.fromisoformat(pred["created_at"])
            horizon = pred["time_horizon_days"] or 30
            expired = datetime.utcnow() > created + timedelta(days=horizon)

            outcome = None
            exit_price = current_price  # default for expiry
            if hit_target:
                outcome = "WIN"
                exit_price = target  # exit at target, not wherever current is now
            elif hit_stop:
                outcome = "LOSS"
                exit_price = stop  # exit at stop, not wherever current is now
            elif expired:
                outcome = "WIN" if ret_pct > 0 else "LOSS"
                # expired: exit at current price (already set)

            # Recalculate return using actual exit_price
            if outcome:
                if direction == "LONG":
                    final_ret_pct = (exit_price - entry) / entry * 100
                else:
                    final_ret_pct = (entry - exit_price) / entry * 100

                resolve_prediction(self.db_path, pred["id"], exit_price, outcome)
                resolved.append({
                    **pred,
                    "current_price": current_price,
                    "exit_price": exit_price,
                    "return_pct": round(final_ret_pct, 2),
                    "outcome": outcome,
                })

        return resolved

    def get_track_record(self) -> TrackRecord:
        """Aggregate performance across all predictions."""
        all_preds = get_all_predictions(self.db_path)

        if not all_preds:
            return TrackRecord(
                total_predictions=0, resolved=0, open=0, wins=0, losses=0,
                expired=0, win_rate=0, avg_return_pct=0, best_trade="N/A",
                worst_trade="N/A", avg_confidence=0, sharpe_estimate=0,
            )

        resolved = [p for p in all_preds if p["outcome"] in ("WIN", "LOSS")]
        open_preds = [p for p in all_preds if p["outcome"] == "OPEN"]
        wins = [p for p in resolved if p["outcome"] == "WIN"]
        losses = [p for p in resolved if p["outcome"] == "LOSS"]

        # Calculate returns
        returns = []
        best_return = -999
        worst_return = 999
        best_trade = "N/A"
        worst_trade = "N/A"

        for p in resolved:
            if p["entry_price"] and p["exit_price"] and p["entry_price"] > 0:
                if p["direction"] == "LONG":
                    ret = (p["exit_price"] - p["entry_price"]) / p["entry_price"] * 100
                else:
                    ret = (p["entry_price"] - p["exit_price"]) / p["entry_price"] * 100
                returns.append(ret)

                if ret > best_return:
                    best_return = ret
                    best_trade = f"{p['ticker']} {p['direction']} ({ret:+.1f}%)"
                if ret < worst_return:
                    worst_return = ret
                    worst_trade = f"{p['ticker']} {p['direction']} ({ret:+.1f}%)"

        avg_return = sum(returns) / len(returns) if returns else 0
        win_rate = len(wins) / len(resolved) if resolved else 0

        # Sharpe ratio (annualized, excess returns over risk-free rate)
        if len(returns) >= 2:
            import numpy as np
            returns_arr = np.array(returns)
            # Convert annual risk-free rate to per-trade rate
            # (rough: assume each prediction spans ~DEFAULT_TIME_HORIZON_DAYS)
            rf_per_trade = RISK_FREE_RATE_ANNUAL * (30 / TRADING_DAYS_PER_YEAR)
            excess_returns = returns_arr - rf_per_trade
            sharpe = (excess_returns.mean() / excess_returns.std()) * (TRADING_DAYS_PER_YEAR ** 0.5) if excess_returns.std() > 0 else 0
        else:
            sharpe = 0.0

        avg_confidence = sum(p.get("confidence", 0) or 0 for p in all_preds) / len(all_preds)

        return TrackRecord(
            total_predictions=len(all_preds),
            resolved=len(resolved),
            open=len(open_preds),
            wins=len(wins),
            losses=len(losses),
            expired=0,
            win_rate=win_rate,
            avg_return_pct=avg_return,
            best_trade=best_trade,
            worst_trade=worst_trade,
            avg_confidence=avg_confidence,
            sharpe_estimate=sharpe,
        )
