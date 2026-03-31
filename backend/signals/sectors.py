from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime

import yfinance as yf
import pandas as pd


SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

DEFENSIVE = {"XLP", "XLU", "XLV", "XLRE"}
CYCLICAL = {"XLY", "XLI", "XLB", "XLF", "XLK"}


@dataclass
class SectorSignal:
    returns_5d: dict[str, float]    # ticker -> 5d return %
    returns_20d: dict[str, float]   # ticker -> 20d return %
    relative_strength: dict[str, float]  # vs SPY
    leaders: list[str]              # top 3 sectors by 5d return
    laggards: list[str]             # bottom 3
    rotation_signal: str            # risk_on, risk_off, mixed
    flags: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


def get_sector_signal() -> SectorSignal:
    returns_5d = {}
    returns_20d = {}
    relative_strength = {}
    flags = []

    # Fetch SPY as benchmark
    spy_data = yf.Ticker("SPY").history(period="60d")
    spy_5d = float(spy_data["Close"].iloc[-1] / spy_data["Close"].iloc[-5] - 1) * 100 if len(spy_data) > 5 else 0

    for ticker in SECTOR_ETFS:
        try:
            data = yf.Ticker(ticker).history(period="60d")
            if data.empty or len(data) < 5:
                continue
            close = data["Close"]
            ret_5d = float(close.iloc[-1] / close.iloc[-5] - 1) * 100
            ret_20d = float(close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) > 20 else 0
            returns_5d[ticker] = round(ret_5d, 2)
            returns_20d[ticker] = round(ret_20d, 2)
            relative_strength[ticker] = round(ret_5d - spy_5d, 2)
        except Exception:
            continue

    # Sort by 5d returns for leaders/laggards
    sorted_sectors = sorted(returns_5d.items(), key=lambda x: x[1], reverse=True)
    leaders = [f"{t} ({SECTOR_ETFS[t]})" for t, _ in sorted_sectors[:3]]
    laggards = [f"{t} ({SECTOR_ETFS[t]})" for t, _ in sorted_sectors[-3:]]

    # Rotation signal: compare defensive vs cyclical average returns
    def_avg = sum(returns_5d.get(t, 0) for t in DEFENSIVE) / max(len(DEFENSIVE), 1)
    cyc_avg = sum(returns_5d.get(t, 0) for t in CYCLICAL) / max(len(CYCLICAL), 1)

    if cyc_avg - def_avg > 1.0:
        rotation_signal = "risk_on"
    elif def_avg - cyc_avg > 1.0:
        rotation_signal = "risk_off"
    else:
        rotation_signal = "mixed"

    # Flags
    if rotation_signal == "risk_off":
        flags.append(f"Defensive sectors outperforming cyclicals by {def_avg - cyc_avg:.1f}pp — risk-off rotation")
    if rotation_signal == "risk_on":
        flags.append(f"Cyclicals outperforming defensives by {cyc_avg - def_avg:.1f}pp — risk-on rotation")

    # Check for extreme sector divergence
    if sorted_sectors:
        spread = sorted_sectors[0][1] - sorted_sectors[-1][1]
        if spread > 5.0:
            flags.append(f"Sector spread at {spread:.1f}pp — extreme divergence between {sorted_sectors[0][0]} and {sorted_sectors[-1][0]}")

    # Energy-specific flags
    if "XLE" in returns_5d and returns_5d["XLE"] > 3.0:
        flags.append(f"Energy sector surging {returns_5d['XLE']:+.1f}% — commodity inflation signal")
    if "XLE" in returns_5d and returns_5d["XLE"] < -3.0:
        flags.append(f"Energy sector dropping {returns_5d['XLE']:+.1f}% — demand destruction signal")

    return SectorSignal(
        returns_5d=returns_5d,
        returns_20d=returns_20d,
        relative_strength=relative_strength,
        leaders=leaders,
        laggards=laggards,
        rotation_signal=rotation_signal,
        flags=flags,
    )
