"""Filing Intelligence Tracker — coordinates all filing signal layers.

Layer 1 (Faster Filings): Form 3/4 (2 days), 13D/13G (10 days)
Layer 2 (Real-time Inference): Options flow, ETF flows, earnings call language
Layer 3 (Predictive): Predictive 13F models — front-run expected filings

Each layer has different timeliness and confidence profiles.
The tracker aggregates them into a unified view, ranked by actionability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from backend.config import Config
from backend.filings.edgar_13f import get_holding_changes, NOTABLE_FUNDS
from backend.filings.edgar_13dg import get_recent_13dg_filings
from backend.filings.form34 import get_recent_insider_transactions
from backend.filings.options_flow import scan_options_flow
from backend.filings.etf_flows import analyze_etf_flows
from backend.filings.earnings_inference import analyze_recent_earnings
from backend.filings.predictive_13f import Predictive13FModel


@dataclass
class FilingSignal:
    layer: str  # layer1_filing, layer2_realtime, layer3_predictive
    source: str  # form4, 13dg, options_flow, etf_flows, earnings, predictive_13f
    investor_name: str
    ticker: str
    signal_type: str  # BUY, SELL, BULLISH, BEARISH, ACCUMULATION, etc.
    confidence: float
    timeliness: str  # real_time, days, weeks
    details: str
    reasoning: list[str] = field(default_factory=list)
    editable: bool = False  # user can validate/invalidate predictive signals

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "source": self.source,
            "investor_name": self.investor_name,
            "ticker": self.ticker,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "timeliness": self.timeliness,
            "details": self.details,
            "reasoning": self.reasoning,
            "editable": self.editable,
        }


@dataclass
class FilingIntelReport:
    timestamp: str
    layer1_signals: list[FilingSignal]
    layer2_signals: list[FilingSignal]
    layer3_signals: list[FilingSignal]
    all_signals: list[FilingSignal]
    flags: list[str]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "layer1_signals": [s.to_dict() for s in self.layer1_signals],
            "layer2_signals": [s.to_dict() for s in self.layer2_signals],
            "layer3_signals": [s.to_dict() for s in self.layer3_signals],
            "total_signals": len(self.all_signals),
            "flags": self.flags,
        }

    def to_summary(self) -> str:
        lines = [
            f"=== FILING INTELLIGENCE REPORT ({self.timestamp}) ===",
            f"Total Signals: {len(self.all_signals)}",
            f"  Layer 1 (Fast Filings): {len(self.layer1_signals)}",
            f"  Layer 2 (Real-time): {len(self.layer2_signals)}",
            f"  Layer 3 (Predictive): {len(self.layer3_signals)}",
            "",
        ]
        for s in self.all_signals[:15]:  # Top 15 signals
            lines.append(f"  [{s.layer}] {s.source}: {s.ticker} — {s.signal_type} "
                         f"(conf: {s.confidence:.0%}, {s.timeliness})")
            if s.details:
                lines.append(f"    {s.details}")

        if self.flags:
            lines.append("\n--- FLAGS ---")
            for f in self.flags:
                lines.append(f"  ! {f}")

        return "\n".join(lines)


class FilingTracker:
    def __init__(self, config: Config):
        self.config = config
        self.predictive_model = Predictive13FModel(config)

    def run_full_scan(self, market_context: str = "") -> FilingIntelReport:
        """Run all filing intelligence layers and return unified report."""
        layer1 = self._scan_layer1()
        layer2 = self._scan_layer2()
        layer3 = self._scan_layer3(market_context, layer1 + layer2)

        all_signals = layer1 + layer2 + layer3
        all_signals.sort(key=lambda s: s.confidence, reverse=True)

        flags = self._generate_flags(all_signals)

        return FilingIntelReport(
            timestamp=datetime.utcnow().isoformat(),
            layer1_signals=layer1,
            layer2_signals=layer2,
            layer3_signals=layer3,
            all_signals=all_signals,
            flags=flags,
        )

    def _scan_layer1(self) -> list[FilingSignal]:
        """Layer 1: Fast filings — Form 3/4 and 13D/13G."""
        signals = []

        # Form 3/4 insider transactions
        try:
            insider_txs = get_recent_insider_transactions()
            for tx in insider_txs[:20]:
                if tx.transaction_type in ("BUY", "SELL"):
                    signals.append(FilingSignal(
                        layer="layer1_filing",
                        source="form4",
                        investor_name=tx.insider_name,
                        ticker=tx.ticker or tx.company,
                        signal_type=tx.transaction_type,
                        confidence=0.7 if tx.transaction_type == "BUY" else 0.5,
                        timeliness="days",
                        details=f"{tx.insider_name} ({tx.insider_title}) {tx.transaction_type} "
                                f"{tx.shares:.0f} shares of {tx.company}",
                    ))
        except Exception as e:
            print(f"Layer 1 Form 4 error: {e}")

        # 13D/13G filings
        try:
            dg_filings = get_recent_13dg_filings()
            for f in dg_filings[:10]:
                signals.append(FilingSignal(
                    layer="layer1_filing",
                    source="13dg",
                    investor_name=f.investor_name,
                    ticker=f.target_ticker or f.target_company,
                    signal_type="ACTIVIST" if f.filing_type == "13D" else "PASSIVE_5PCT",
                    confidence=0.75 if f.filing_type == "13D" else 0.6,
                    timeliness="days",
                    details=f"{f.investor_name} filed {f.filing_type} for {f.target_company} "
                            f"({f.ownership_pct:.1f}% ownership)",
                ))
        except Exception as e:
            print(f"Layer 1 13D/G error: {e}")

        return signals

    def _scan_layer2(self) -> list[FilingSignal]:
        """Layer 2: Real-time inference — options flow, ETF flows, earnings."""
        signals = []

        # Options flow
        try:
            options = scan_options_flow()
            for o in options[:10]:
                signals.append(FilingSignal(
                    layer="layer2_realtime",
                    source="options_flow",
                    investor_name="Institutional (inferred)",
                    ticker=o.ticker,
                    signal_type="BULLISH" if o.direction == "bullish" else "BEARISH",
                    confidence=o.confidence,
                    timeliness="real_time",
                    details=o.details,
                ))
        except Exception as e:
            print(f"Layer 2 options error: {e}")

        # ETF flows
        try:
            etf_signals = analyze_etf_flows()
            for ef in etf_signals[:10]:
                signals.append(FilingSignal(
                    layer="layer2_realtime",
                    source="etf_flows",
                    investor_name="Institutional (aggregated)",
                    ticker=ef.ticker,
                    signal_type="ACCUMULATION" if ef.direction == "inflow" else "DISTRIBUTION",
                    confidence=ef.confidence,
                    timeliness="real_time",
                    details=ef.details,
                ))
        except Exception as e:
            print(f"Layer 2 ETF flows error: {e}")

        # Earnings inference
        try:
            earnings = analyze_recent_earnings(self.config.perplexity_api_key)
            for ei in earnings:
                signals.append(FilingSignal(
                    layer="layer2_realtime",
                    source="earnings",
                    investor_name="Market consensus",
                    ticker=ei.ticker,
                    signal_type=ei.signal.upper(),
                    confidence=ei.confidence,
                    timeliness="days",
                    details=ei.details,
                ))
        except Exception as e:
            print(f"Layer 2 earnings error: {e}")

        return signals

    def _scan_layer3(self, market_context: str, existing_signals: list[FilingSignal]) -> list[FilingSignal]:
        """Layer 3: Predictive 13F — front-run expected filings."""
        signals = []

        # Gather supporting signal summaries for the predictive model
        supporting = [f"{s.source}: {s.ticker} {s.signal_type} ({s.details[:80]})" for s in existing_signals[:15]]

        try:
            all_predictions = self.predictive_model.predict_all_tracked_funds(
                market_context, supporting
            )

            for fund_key, predictions in all_predictions.items():
                for p in predictions:
                    signals.append(FilingSignal(
                        layer="layer3_predictive",
                        source="predictive_13f",
                        investor_name=p.fund_name,
                        ticker=p.ticker,
                        signal_type=f"PREDICTED_{p.predicted_action}",
                        confidence=p.confidence,
                        timeliness="weeks",
                        details=f"Predicted: {p.fund_name} likely to {p.predicted_action} {p.ticker}",
                        reasoning=p.reasoning,
                        editable=True,
                    ))
        except Exception as e:
            print(f"Layer 3 predictive error: {e}")

        return signals

    def _generate_flags(self, all_signals: list[FilingSignal]) -> list[str]:
        """Generate high-level flags from aggregated signals."""
        flags = []

        # Count bullish/bearish signals per ticker
        ticker_signals: dict[str, dict] = {}
        for s in all_signals:
            if s.ticker not in ticker_signals:
                ticker_signals[s.ticker] = {"bullish": 0, "bearish": 0}
            if s.signal_type in ("BUY", "BULLISH", "ACCUMULATION", "PREDICTED_BUY", "PREDICTED_INCREASE"):
                ticker_signals[s.ticker]["bullish"] += 1
            elif s.signal_type in ("SELL", "BEARISH", "DISTRIBUTION", "PREDICTED_SELL", "PREDICTED_DECREASE"):
                ticker_signals[s.ticker]["bearish"] += 1

        for ticker, counts in ticker_signals.items():
            if counts["bullish"] >= 3:
                flags.append(f"CONVERGENT BULLISH: {ticker} has {counts['bullish']} bullish signals across layers")
            if counts["bearish"] >= 3:
                flags.append(f"CONVERGENT BEARISH: {ticker} has {counts['bearish']} bearish signals across layers")

        return flags
