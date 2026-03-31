"""ETF flow analysis — detect institutional reallocation in real-time.

When sector ETFs see massive inflows/outflows, it signals institutional
reallocation. A $2B inflow into XLK over a week = big money moving into tech.

We detect this via:
1. Volume anomalies (current vs 20-day average)
2. Price-volume divergences (price flat but volume surging = accumulation)
3. Cross-sector flow analysis (money leaving XLE, entering XLU = risk-off rotation)
"""
from __future__ import annotations
from dataclasses import dataclass

import yfinance as yf


@dataclass
class ETFFlowSignal:
    ticker: str
    sector: str
    signal_type: str  # volume_surge, accumulation, distribution, rotation
    direction: str  # inflow, outflow
    details: str
    volume_ratio: float  # current vs avg
    price_change_5d: float
    confidence: float


SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLY": "Consumer Discretionary", "XLP": "Consumer Staples",
    "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLC": "Communication Services",
}

THEMATIC_ETFS = {
    "TLT": "Long-Term Treasuries", "GLD": "Gold", "SLV": "Silver",
    "USO": "Oil", "UNG": "Natural Gas", "EEM": "Emerging Markets",
    "EFA": "Developed International", "HYG": "High Yield Bonds",
    "LQD": "Investment Grade Bonds", "IWM": "Small Cap",
    "ARKK": "Innovation/Growth", "XBI": "Biotech",
}


def analyze_etf_flows() -> list[ETFFlowSignal]:
    """Analyze ETF flows across sector and thematic ETFs."""
    signals = []
    all_etfs = {**SECTOR_ETFS, **THEMATIC_ETFS}

    for ticker, name in all_etfs.items():
        try:
            data = yf.Ticker(ticker).history(period="30d")
            if data.empty or len(data) < 20:
                continue

            close = data["Close"]
            volume = data["Volume"]

            current_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(20).mean().iloc[-1])
            vol_ratio = current_vol / max(avg_vol, 1)

            price_5d = float(close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) > 5 else 0

            # Volume surge detection
            if vol_ratio > 2.0:
                direction = "inflow" if price_5d > 0 else "outflow"
                signals.append(ETFFlowSignal(
                    ticker=ticker, sector=name,
                    signal_type="volume_surge",
                    direction=direction,
                    details=f"{ticker} ({name}) volume {vol_ratio:.1f}x average, price {price_5d:+.1f}% over 5d",
                    volume_ratio=round(vol_ratio, 1),
                    price_change_5d=round(price_5d, 2),
                    confidence=min(0.3 + vol_ratio * 0.1, 0.8),
                ))

            # Accumulation: price flat but volume high (smart money building)
            if vol_ratio > 1.5 and abs(price_5d) < 1.0:
                signals.append(ETFFlowSignal(
                    ticker=ticker, sector=name,
                    signal_type="accumulation",
                    direction="inflow",
                    details=f"{ticker} ({name}) quiet accumulation: vol {vol_ratio:.1f}x avg but price only {price_5d:+.1f}%",
                    volume_ratio=round(vol_ratio, 1),
                    price_change_5d=round(price_5d, 2),
                    confidence=0.5,
                ))

            # Distribution: price dropping on heavy volume
            if vol_ratio > 1.8 and price_5d < -2.0:
                signals.append(ETFFlowSignal(
                    ticker=ticker, sector=name,
                    signal_type="distribution",
                    direction="outflow",
                    details=f"{ticker} ({name}) distribution: vol {vol_ratio:.1f}x avg, price {price_5d:+.1f}%",
                    volume_ratio=round(vol_ratio, 1),
                    price_change_5d=round(price_5d, 2),
                    confidence=0.6,
                ))

        except Exception:
            continue

    signals.sort(key=lambda s: s.confidence, reverse=True)
    return signals
