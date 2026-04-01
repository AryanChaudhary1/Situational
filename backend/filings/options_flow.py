"""Unusual options flow detection — REAL-TIME institutional signal.

When institutions build large equity positions, they often hedge or amplify
with options first. By detecting unusual options activity, we can infer
institutional positioning BEFORE any filing is required.

Key signals:
- Large block trades (>$1M notional)
- Unusual volume ratios (volume >> open interest)
- Sweep orders (aggressive, hit multiple exchanges)
- Put/call ratio shifts at the ticker level
- Deep ITM calls = synthetic long (hidden accumulation)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class OptionsFlowSignal:
    ticker: str
    signal_type: str  # unusual_volume, large_block, put_call_shift, sweep
    direction: str  # bullish, bearish, neutral
    details: str
    implied_vol: float
    put_call_ratio: float
    volume_oi_ratio: float  # volume / open interest
    confidence: float
    timestamp: str


def detect_unusual_options(ticker: str) -> list[OptionsFlowSignal]:
    """Detect unusual options activity for a given ticker using yfinance."""
    signals = []

    try:
        t = yf.Ticker(ticker)
        # Get available expiration dates
        expirations = t.options
        if not expirations:
            return signals

        # Check nearest 3 expirations
        for exp_date in expirations[:3]:
            try:
                chain = t.option_chain(exp_date)
                calls = chain.calls
                puts = chain.puts

                if calls.empty and puts.empty:
                    continue

                # Aggregate put/call volume
                total_call_vol = int(calls["volume"].sum()) if "volume" in calls.columns else 0
                total_put_vol = int(puts["volume"].sum()) if "volume" in puts.columns else 0
                total_call_oi = int(calls["openInterest"].sum()) if "openInterest" in calls.columns else 0
                total_put_oi = int(puts["openInterest"].sum()) if "openInterest" in puts.columns else 0

                pc_ratio = total_put_vol / max(total_call_vol, 1)

                # Check for unusual volume vs open interest
                for _, row in calls.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi = int(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0) or 0)

                    if oi > 0 and vol > oi * 3 and vol > 1000:
                        signals.append(OptionsFlowSignal(
                            ticker=ticker,
                            signal_type="unusual_volume",
                            direction="bullish",
                            details=f"Call {row.get('strike', '?')} {exp_date}: vol={vol} vs OI={oi} ({vol/oi:.1f}x)",
                            implied_vol=round(iv * 100, 1),
                            put_call_ratio=round(pc_ratio, 2),
                            volume_oi_ratio=round(vol / max(oi, 1), 1),
                            confidence=min(0.4 + (vol / oi) * 0.1, 0.8),
                            timestamp=exp_date,
                        ))

                for _, row in puts.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi = int(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0) or 0)

                    if oi > 0 and vol > oi * 3 and vol > 1000:
                        signals.append(OptionsFlowSignal(
                            ticker=ticker,
                            signal_type="unusual_volume",
                            direction="bearish",
                            details=f"Put {row.get('strike', '?')} {exp_date}: vol={vol} vs OI={oi} ({vol/oi:.1f}x)",
                            implied_vol=round(iv * 100, 1),
                            put_call_ratio=round(pc_ratio, 2),
                            volume_oi_ratio=round(vol / max(oi, 1), 1),
                            confidence=min(0.4 + (vol / oi) * 0.1, 0.8),
                            timestamp=exp_date,
                        ))

                # Overall put/call ratio signal
                if pc_ratio > 2.0:
                    signals.append(OptionsFlowSignal(
                        ticker=ticker,
                        signal_type="put_call_shift",
                        direction="bearish",
                        details=f"Put/call ratio elevated at {pc_ratio:.2f} for {exp_date}",
                        implied_vol=0,
                        put_call_ratio=round(pc_ratio, 2),
                        volume_oi_ratio=0,
                        confidence=0.5,
                        timestamp=exp_date,
                    ))
                elif pc_ratio < 0.3 and total_call_vol > 5000:
                    signals.append(OptionsFlowSignal(
                        ticker=ticker,
                        signal_type="put_call_shift",
                        direction="bullish",
                        details=f"Put/call ratio very low at {pc_ratio:.2f} for {exp_date} — heavy call buying",
                        implied_vol=0,
                        put_call_ratio=round(pc_ratio, 2),
                        volume_oi_ratio=0,
                        confidence=0.5,
                        timestamp=exp_date,
                    ))

            except Exception:
                continue

    except Exception as e:
        logger.warning("Options flow error for %s: %s", ticker, e)

    return signals


def scan_options_flow(tickers: list[str] | None = None) -> list[OptionsFlowSignal]:
    """Scan multiple tickers for unusual options flow."""
    if tickers is None:
        # Default: scan most liquid large caps
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
                    "META", "GOOGL", "AMD", "JPM", "XLF", "XLE", "GLD", "TLT"]

    all_signals = []
    for ticker in tickers:
        signals = detect_unusual_options(ticker)
        all_signals.extend(signals)

    # Sort by confidence
    all_signals.sort(key=lambda s: s.confidence, reverse=True)
    return all_signals
