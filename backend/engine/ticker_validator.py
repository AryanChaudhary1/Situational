from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

import yfinance as yf


@dataclass
class TickerInfo:
    symbol: str
    name: str
    price: float
    market_cap: float
    avg_volume: float
    sector: str
    asset_type: str  # stock, etf, crypto

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "market_cap": self.market_cap,
            "avg_volume": self.avg_volume,
            "sector": self.sector,
            "asset_type": self.asset_type,
        }


def validate_ticker(symbol: str, min_volume: int = 100_000, min_market_cap: float = 1e8) -> TickerInfo | None:
    """Validate a ticker exists, is liquid, and return its info. Returns None if invalid."""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}

        # Must have a valid price
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if not price or price <= 0:
            return None

        market_cap = info.get("marketCap", 0) or 0
        avg_volume = info.get("averageVolume", 0) or 0

        # Determine asset type
        quote_type = info.get("quoteType", "").upper()
        if quote_type == "ETF":
            asset_type = "etf"
            # ETFs don't have market cap in the same way, skip that check
        elif quote_type == "CRYPTOCURRENCY":
            asset_type = "crypto"
        else:
            asset_type = "stock"
            if market_cap < min_market_cap:
                return None

        if avg_volume < min_volume and asset_type != "crypto":
            return None

        return TickerInfo(
            symbol=symbol.upper(),
            name=info.get("shortName", symbol),
            price=round(float(price), 2),
            market_cap=float(market_cap),
            avg_volume=float(avg_volume),
            sector=info.get("sector", "N/A"),
            asset_type=asset_type,
        )
    except Exception:
        return None


def validate_tickers(symbols: list[str]) -> dict[str, TickerInfo | None]:
    """Validate multiple tickers. Returns dict of symbol -> TickerInfo or None."""
    return {s: validate_ticker(s) for s in symbols}


def get_current_price(symbol: str) -> float | None:
    """Quick price lookup for a single ticker."""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0))
    except Exception:
        return None
