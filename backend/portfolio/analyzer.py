"""Portfolio analyzer — connects holdings to the causal engine for WHY analysis."""
from __future__ import annotations

from backend.config import Config
from backend.engine.causal_engine import CausalEngine, HoldingAnalysis
from backend.filings.edgar_13f import HoldingChange


class PortfolioAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.engine = CausalEngine(config) if config.anthropic_api_key else None

    def analyze_changes(self, changes: list[HoldingChange],
                        signal_summary: str) -> list[dict]:
        """Analyze WHY investors made these changes."""
        if not self.engine:
            return [{"change": c.__dict__, "analysis": "API key required"} for c in changes]

        results = []
        for change in changes[:5]:  # Limit to top 5 to manage API costs
            try:
                analysis = self.engine.analyze_holding(
                    investor_name=change.investor_name,
                    ticker=change.ticker,
                    shares=change.current_shares,
                    value=change.current_value,
                    change_type=change.change_type,
                    filing_date=change.filing_date,
                    signal_summary=signal_summary,
                )
                results.append({
                    "change": {
                        "investor": change.investor_name,
                        "ticker": change.ticker,
                        "company": change.company_name,
                        "action": change.change_type,
                        "pct_change": change.pct_change,
                        "value": change.current_value,
                    },
                    "analysis": analysis.likely_thesis,
                })
            except Exception as e:
                results.append({
                    "change": {"investor": change.investor_name, "ticker": change.ticker},
                    "analysis": f"Analysis error: {e}",
                })

        return results
