from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from backend.config import Config
from backend.constants import (
    SIGNAL_CACHE_TTL_SECONDS,
    SEVERITY_THRESHOLD_CRISIS,
    SEVERITY_THRESHOLD_ALERT,
    SEVERITY_THRESHOLD_ELEVATED,
    SEVERITY_BONUS_VIX_FEAR,
    SEVERITY_BONUS_VIX_ELEVATED,
    SEVERITY_BONUS_RISK_OFF,
)
from backend.signals.vix import get_vix_signal, VixSignal
from backend.signals.yield_curve import get_yield_curve_signal, YieldCurveSignal
from backend.signals.currency import get_currency_signal, CurrencySignal
from backend.signals.sectors import get_sector_signal, SectorSignal
from backend.signals.news import get_news_signal_perplexity, NewsSignal


@dataclass
class SignalReport:
    timestamp: str
    vix: VixSignal
    yield_curve: YieldCurveSignal
    currency: CurrencySignal
    sectors: SectorSignal
    news: NewsSignal
    all_flags: list[str]
    severity: str  # calm, elevated, alert, crisis

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "vix": self.vix.to_dict(),
            "yield_curve": self.yield_curve.to_dict(),
            "currency": self.currency.to_dict(),
            "sectors": self.sectors.to_dict(),
            "news": self.news.to_dict(),
            "all_flags": self.all_flags,
            "severity": self.severity,
        }

    def to_summary(self) -> str:
        """Human-readable summary for LLM consumption."""
        lines = [
            f"=== MARKET SIGNAL REPORT ({self.timestamp}) ===",
            f"Overall Severity: {self.severity.upper()}",
            "",
            f"--- VIX ---",
            f"Level: {self.vix.current} | Regime: {self.vix.regime} | Term Structure: {self.vix.term_structure}",
            f"Day Change: {self.vix.day_change:+.1f}% | Week: {self.vix.week_change:+.1f}% | 1Y Percentile: {self.vix.percentile_1y:.0f}th",
            "",
            f"--- YIELD CURVE ---",
            f"2s10s Spread: {self.yield_curve.spread_2s10s:.3f} | Shape: {self.yield_curve.curve_shape} | Trend: {self.yield_curve.steepening_trend}",
            "",
            f"--- CURRENCIES ---",
        ]
        for name, level in self.currency.levels.items():
            chg = self.currency.changes_1d.get(name, 0)
            lines.append(f"  {name.upper()}: {level} ({chg:+.2f}% 1d)")
        lines += [
            "",
            f"--- SECTOR ROTATION ---",
            f"Signal: {self.sectors.rotation_signal}",
            f"Leaders: {', '.join(self.sectors.leaders)}",
            f"Laggards: {', '.join(self.sectors.laggards)}",
            "",
            f"--- NEWS ---",
            f"Sentiment: {self.news.sentiment_summary}",
            f"Themes: {', '.join(self.news.themes[:5])}",
        ]
        if self.news.top_stories:
            lines.append("Top Stories:")
            for s in self.news.top_stories[:5]:
                lines.append(f"  - {s['title']}")
        lines += ["", "--- FLAGS ---"]
        for f in self.all_flags:
            lines.append(f"  ! {f}")
        return "\n".join(lines)


def classify_severity(all_flags: list[str], vix: VixSignal, sectors: SectorSignal) -> str:
    score = len(all_flags)
    if vix.regime == "fear":
        score += SEVERITY_BONUS_VIX_FEAR
    elif vix.regime == "elevated":
        score += SEVERITY_BONUS_VIX_ELEVATED
    if sectors.rotation_signal == "risk_off":
        score += SEVERITY_BONUS_RISK_OFF

    if score >= SEVERITY_THRESHOLD_CRISIS:
        return "crisis"
    elif score >= SEVERITY_THRESHOLD_ALERT:
        return "alert"
    elif score >= SEVERITY_THRESHOLD_ELEVATED:
        return "elevated"
    return "calm"


class SignalScanner:
    def __init__(self, config: Config):
        self.config = config
        self._cache: SignalReport | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl_seconds = SIGNAL_CACHE_TTL_SECONDS

    def scan_all(self) -> SignalReport:
        # Return cached result if fresh (within TTL)
        if self._cache and self._cache_time:
            age = (datetime.utcnow() - self._cache_time).total_seconds()
            if age < self._cache_ttl_seconds:
                return self._cache

        # Otherwise, scan fresh and cache
        report = self._scan_fresh()
        self._cache = report
        self._cache_time = datetime.utcnow()
        return report

    def _scan_fresh(self) -> SignalReport:
        """Scan all signals without caching."""
        vix = get_vix_signal()
        yield_curve = get_yield_curve_signal(self.config.fred_api_key)
        currency = get_currency_signal()
        sectors = get_sector_signal()
        news = get_news_signal_perplexity(self.config.perplexity_api_key)

        all_flags = vix.flags + yield_curve.flags + currency.flags + sectors.flags + news.flags
        severity = classify_severity(all_flags, vix, sectors)

        return SignalReport(
            timestamp=datetime.utcnow().isoformat(),
            vix=vix,
            yield_curve=yield_curve,
            currency=currency,
            sectors=sectors,
            news=news,
            all_flags=all_flags,
            severity=severity,
        )
