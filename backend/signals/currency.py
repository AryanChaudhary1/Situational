from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime

import yfinance as yf


CURRENCY_TICKERS = {
    "dxy": "DX-Y.NYB",
    "usdjpy": "JPY=X",
    "eurusd": "EURUSD=X",
    "gold": "GC=F",
    "bitcoin": "BTC-USD",
}


@dataclass
class CurrencySignal:
    levels: dict[str, float]
    changes_1d: dict[str, float]
    changes_5d: dict[str, float]
    changes_20d: dict[str, float]
    flags: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


def _pct_change(series, periods: int) -> float:
    if len(series) <= periods:
        return 0.0
    return round(float(series.iloc[-1] / series.iloc[-periods - 1] - 1) * 100, 2)


def get_currency_signal() -> CurrencySignal:
    levels = {}
    changes_1d = {}
    changes_5d = {}
    changes_20d = {}
    flags = []

    for name, ticker in CURRENCY_TICKERS.items():
        try:
            data = yf.Ticker(ticker).history(period="60d")
            if data.empty:
                continue
            close = data["Close"]
            levels[name] = round(float(close.iloc[-1]), 2)
            changes_1d[name] = _pct_change(close, 1)
            changes_5d[name] = _pct_change(close, 5)
            changes_20d[name] = _pct_change(close, 20)
        except Exception:
            continue

    # Flag detection
    if "usdjpy" in changes_1d:
        if abs(changes_1d["usdjpy"]) > 1.0:
            flags.append(f"USD/JPY moved {changes_1d['usdjpy']:+.2f}% today — carry trade stress signal")
        if "usdjpy" in changes_5d and changes_5d["usdjpy"] < -3.0:
            flags.append("JPY strengthening sharply over 5 days — potential carry trade unwind")

    if "dxy" in changes_5d:
        if changes_5d["dxy"] > 2.0:
            flags.append(f"DXY surging {changes_5d['dxy']:+.2f}% over 5 days — dollar strength")
        elif changes_5d["dxy"] < -2.0:
            flags.append(f"DXY dropping {changes_5d['dxy']:+.2f}% over 5 days — dollar weakness")

    if "gold" in changes_5d and changes_5d["gold"] > 3.0:
        flags.append(f"Gold up {changes_5d['gold']:+.2f}% in 5 days — flight to safety")

    # Gold-DXY divergence check
    if "gold" in changes_5d and "dxy" in changes_5d:
        if changes_5d["gold"] > 2.0 and changes_5d["dxy"] > 1.0:
            flags.append("Gold and DXY both rising — unusual divergence, possible systemic stress")

    return CurrencySignal(
        levels=levels,
        changes_1d=changes_1d,
        changes_5d=changes_5d,
        changes_20d=changes_20d,
        flags=flags,
    )
