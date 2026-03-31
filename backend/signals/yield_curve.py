from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime

import pandas as pd


FRED_SERIES = {
    "1mo": "DGS1MO",
    "3mo": "DGS3MO",
    "6mo": "DGS6MO",
    "1y": "DGS1",
    "2y": "DGS2",
    "5y": "DGS5",
    "10y": "DGS10",
    "30y": "DGS30",
}


@dataclass
class YieldCurveSignal:
    yields: dict[str, float]  # tenor -> yield
    spread_2s10s: float
    spread_3m10y: float
    curve_shape: str  # normal, flat, inverted
    steepening_trend: str  # steepening, flattening, stable
    spread_2s10s_30d_ago: float
    flags: list[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


def get_yield_curve_signal(fred_api_key: str) -> YieldCurveSignal:
    if not fred_api_key:
        return YieldCurveSignal(
            yields={}, spread_2s10s=0, spread_3m10y=0,
            curve_shape="unknown", steepening_trend="unknown",
            spread_2s10s_30d_ago=0, flags=["FRED API key not configured"],
        )

    try:
        from fredapi import Fred
        fred = Fred(api_key=fred_api_key)

        yields = {}
        for tenor, series_id in FRED_SERIES.items():
            try:
                data = fred.get_series(series_id, observation_start="2024-01-01")
                data = data.dropna()
                if not data.empty:
                    yields[tenor] = round(float(data.iloc[-1]), 3)
            except Exception:
                continue

        if "2y" not in yields or "10y" not in yields:
            return YieldCurveSignal(
                yields=yields, spread_2s10s=0, spread_3m10y=0,
                curve_shape="unknown", steepening_trend="unknown",
                spread_2s10s_30d_ago=0, flags=["Insufficient yield data"],
            )

        spread_2s10s = round(yields["10y"] - yields["2y"], 3)
        spread_3m10y = round(yields.get("10y", 0) - yields.get("3mo", 0), 3) if "3mo" in yields else 0

        # Get 30-day-ago spread for trend
        spread_2s10s_30d_ago = spread_2s10s  # fallback
        try:
            y2_hist = fred.get_series("DGS2", observation_start="2024-01-01").dropna()
            y10_hist = fred.get_series("DGS10", observation_start="2024-01-01").dropna()
            if len(y2_hist) > 30 and len(y10_hist) > 30:
                spread_2s10s_30d_ago = round(float(y10_hist.iloc[-30]) - float(y2_hist.iloc[-30]), 3)
        except Exception:
            pass

        # Classify curve shape
        if spread_2s10s < -0.1:
            curve_shape = "inverted"
        elif spread_2s10s < 0.2:
            curve_shape = "flat"
        else:
            curve_shape = "normal"

        # Classify trend
        delta = spread_2s10s - spread_2s10s_30d_ago
        if delta > 0.15:
            steepening_trend = "steepening"
        elif delta < -0.15:
            steepening_trend = "flattening"
        else:
            steepening_trend = "stable"

        flags = []
        if curve_shape == "inverted":
            flags.append(f"Yield curve INVERTED — 2s10s spread at {spread_2s10s:.3f}")
        if spread_3m10y < 0:
            flags.append(f"3m10y spread negative ({spread_3m10y:.3f}) — recession signal")
        if steepening_trend == "steepening" and curve_shape == "inverted":
            flags.append("Curve steepening from inversion — potential recession onset (bear steepener)")
        if steepening_trend == "flattening":
            flags.append("Curve flattening — tightening financial conditions")

        return YieldCurveSignal(
            yields=yields,
            spread_2s10s=spread_2s10s,
            spread_3m10y=spread_3m10y,
            curve_shape=curve_shape,
            steepening_trend=steepening_trend,
            spread_2s10s_30d_ago=spread_2s10s_30d_ago,
            flags=flags,
        )

    except Exception as e:
        return YieldCurveSignal(
            yields={}, spread_2s10s=0, spread_3m10y=0,
            curve_shape="unknown", steepening_trend="unknown",
            spread_2s10s_30d_ago=0, flags=[f"Yield curve error: {e}"],
        )
