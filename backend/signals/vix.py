from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime

import yfinance as yf
import pandas as pd


@dataclass
class VixSignal:
    current: float
    ma_5d: float
    ma_20d: float
    percentile_1y: float
    regime: str  # low, normal, elevated, fear
    day_change: float
    week_change: float
    term_structure: str  # contango, backwardation, flat
    flags: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


def classify_regime(level: float) -> str:
    if level < 14:
        return "low"
    elif level < 20:
        return "normal"
    elif level < 30:
        return "elevated"
    return "fear"


def get_vix_signal(lookback_days: int = 252) -> VixSignal:
    vix = yf.Ticker("^VIX")
    hist = vix.history(period=f"{lookback_days}d")

    if hist.empty:
        return VixSignal(
            current=0, ma_5d=0, ma_20d=0, percentile_1y=0,
            regime="unknown", day_change=0, week_change=0,
            term_structure="unknown", flags=["VIX data unavailable"],
        )

    close = hist["Close"]
    current = float(close.iloc[-1])
    ma_5d = float(close.rolling(5).mean().iloc[-1])
    ma_20d = float(close.rolling(20).mean().iloc[-1])
    percentile = float((close < current).sum() / len(close) * 100)

    day_change = float(close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) > 1 else 0
    week_change = float(close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) > 5 else 0

    # Term structure: VIX vs VIX3M
    term_structure = "unknown"
    try:
        vix3m = yf.Ticker("^VIX3M")
        vix3m_hist = vix3m.history(period="5d")
        if not vix3m_hist.empty:
            vix3m_current = float(vix3m_hist["Close"].iloc[-1])
            ratio = current / vix3m_current
            if ratio > 1.05:
                term_structure = "backwardation"
            elif ratio < 0.95:
                term_structure = "contango"
            else:
                term_structure = "flat"
    except Exception:
        pass

    regime = classify_regime(current)

    flags = []
    if regime == "fear":
        flags.append(f"VIX in FEAR regime at {current:.1f}")
    if day_change > 15:
        flags.append(f"VIX spiked {day_change:.1f}% today")
    if term_structure == "backwardation":
        flags.append("VIX term structure in backwardation — near-term fear elevated")
    if current > ma_20d * 1.2:
        flags.append(f"VIX {((current/ma_20d)-1)*100:.0f}% above 20d MA — volatility expanding")
    if current < 12:
        flags.append("VIX extremely low — complacency risk")

    return VixSignal(
        current=round(current, 2),
        ma_5d=round(ma_5d, 2),
        ma_20d=round(ma_20d, 2),
        percentile_1y=round(percentile, 1),
        regime=regime,
        day_change=round(day_change, 2),
        week_change=round(week_change, 2),
        term_structure=term_structure,
        flags=flags,
    )
