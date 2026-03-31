"""Predictive 13F model — THE REAL EDGE. This is what quant funds do.

Instead of waiting 45 days for 13F filings, we PREDICT what funds will disclose
by tracking:
1. Past 13F behavior patterns per fund
2. Sector rotation patterns + market conditions
3. Fund factor exposures (momentum, value, growth, quality)
4. Current signals from other layers (options, ETF flows, insider tx)

The model: "Given market condition X, Fund Y historically does Z."
This is systematic front-running of expected filing information.

We display the model's reasoning and let the user validate/invalidate/edit predictions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import json

import anthropic

from backend.config import Config


@dataclass
class FundBehaviorProfile:
    fund_name: str
    style: str  # value, growth, momentum, macro, multi_strategy
    typical_sectors: list[str]
    rebalance_pattern: str  # quarterly, monthly, event_driven
    known_factors: list[str]  # momentum, quality, low_vol, etc.
    historical_notes: str


@dataclass
class Predicted13FChange:
    fund_name: str
    ticker: str
    predicted_action: str  # BUY, SELL, INCREASE, DECREASE
    confidence: float
    reasoning: list[str]  # multi-step reasoning chain
    supporting_signals: list[str]  # which signals support this
    market_condition: str
    editable: bool = True  # user can validate/invalidate
    user_validated: bool | None = None  # None = not reviewed, True/False = user decision
    actual_outcome: str | None = None  # filled when 13F is actually filed
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "fund_name": self.fund_name,
            "ticker": self.ticker,
            "predicted_action": self.predicted_action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "supporting_signals": self.supporting_signals,
            "market_condition": self.market_condition,
            "editable": self.editable,
            "user_validated": self.user_validated,
            "actual_outcome": self.actual_outcome,
            "created_at": self.created_at,
        }


# Known fund behavior profiles (built from historical 13F analysis)
FUND_PROFILES = {
    "berkshire_hathaway": FundBehaviorProfile(
        fund_name="Berkshire Hathaway",
        style="value",
        typical_sectors=["Financials", "Consumer Staples", "Energy", "Technology"],
        rebalance_pattern="quarterly",
        known_factors=["value", "quality", "low_vol"],
        historical_notes="Concentrated portfolio. Holds for years. Recent pivot into tech (AAPL). Buys on fear. Sells slowly.",
    ),
    "renaissance": FundBehaviorProfile(
        fund_name="Renaissance Technologies",
        style="multi_strategy",
        typical_sectors=["Technology", "Healthcare", "Financials"],
        rebalance_pattern="monthly",
        known_factors=["momentum", "mean_reversion", "statistical_arbitrage"],
        historical_notes="High turnover quant fund. 3000+ positions. Exploits short-term mispricings. Medallion fund is the edge.",
    ),
    "bridgewater": FundBehaviorProfile(
        fund_name="Bridgewater Associates",
        style="macro",
        typical_sectors=["Broad market ETFs", "Emerging Markets", "Gold", "Bonds"],
        rebalance_pattern="quarterly",
        known_factors=["risk_parity", "macro", "inflation_hedge"],
        historical_notes="Risk parity approach. Heavy ETF user. All Weather portfolio. Adjusts based on macro regime.",
    ),
    "pershing_square": FundBehaviorProfile(
        fund_name="Pershing Square Capital",
        style="value",
        typical_sectors=["Consumer", "Real Estate", "Technology"],
        rebalance_pattern="event_driven",
        known_factors=["value", "activist", "concentrated"],
        historical_notes="Concentrated 8-12 positions. Activist investor. Big macro bets (rates hedges). Public about positions.",
    ),
    "citadel": FundBehaviorProfile(
        fund_name="Citadel Advisors",
        style="multi_strategy",
        typical_sectors=["Technology", "Healthcare", "Financials", "Energy"],
        rebalance_pattern="monthly",
        known_factors=["momentum", "event_driven", "relative_value"],
        historical_notes="Multi-strategy. Huge options book. Very high turnover. Uses all instruments.",
    ),
}


class Predictive13FModel:
    def __init__(self, config: Config):
        self.config = config
        if config.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        else:
            self.client = None

    def predict_fund_moves(self, fund_key: str, market_context: str,
                           supporting_signals: list[str] | None = None) -> list[Predicted13FChange]:
        """Predict what a fund will likely do in the next 13F based on current conditions."""
        if not self.client:
            return []

        profile = FUND_PROFILES.get(fund_key)
        if not profile:
            return []

        signals_text = "\n".join(f"- {s}" for s in (supporting_signals or []))

        prompt = f"""You are a quantitative analyst predicting what {profile.fund_name} will likely
disclose in their next 13F filing, based on their known investment style and current market conditions.

FUND PROFILE:
- Style: {profile.style}
- Typical Sectors: {', '.join(profile.typical_sectors)}
- Rebalance Pattern: {profile.rebalance_pattern}
- Known Factors: {', '.join(profile.known_factors)}
- Historical Notes: {profile.historical_notes}

CURRENT MARKET CONDITIONS:
{market_context}

SUPPORTING SIGNALS (from options flow, ETF flows, insider activity):
{signals_text if signals_text else "No additional signals available"}

Based on the fund's historical behavior patterns combined with current market conditions,
predict their 3-5 most likely portfolio changes. For each prediction, provide a multi-step
reasoning chain explaining WHY this fund would make this move NOW.

Respond as JSON:
{{
  "predictions": [
    {{
      "ticker": "SYMBOL",
      "action": "BUY|SELL|INCREASE|DECREASE",
      "confidence": 0.0-1.0,
      "reasoning": ["Step 1: ...", "Step 2: ...", "Therefore: ..."],
      "supporting_signals": ["signal1", "signal2"],
      "market_condition_trigger": "what current condition triggered this prediction"
    }}
  ]
}}"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system="You are a quantitative fund analyst. Respond only with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
            )

            import re
            content = response.content[0].text
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            predictions = []

            for p in data.get("predictions", []):
                predictions.append(Predicted13FChange(
                    fund_name=profile.fund_name,
                    ticker=p.get("ticker", ""),
                    predicted_action=p.get("action", "UNKNOWN"),
                    confidence=float(p.get("confidence", 0.3)),
                    reasoning=p.get("reasoning", []),
                    supporting_signals=p.get("supporting_signals", []),
                    market_condition=p.get("market_condition_trigger", ""),
                ))

            return predictions

        except Exception as e:
            print(f"Predictive 13F error for {fund_key}: {e}")
            return []

    def predict_all_tracked_funds(self, market_context: str,
                                   supporting_signals: list[str] | None = None) -> dict[str, list[Predicted13FChange]]:
        """Run predictions for all tracked funds."""
        all_predictions = {}
        for fund_key in FUND_PROFILES:
            predictions = self.predict_fund_moves(fund_key, market_context, supporting_signals)
            if predictions:
                all_predictions[fund_key] = predictions
        return all_predictions
