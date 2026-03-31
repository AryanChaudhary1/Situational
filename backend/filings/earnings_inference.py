"""Infer institutional positioning from earnings call language + sector moves.

Funds build themes. If Bridgewater is long "AI infrastructure", they hold NVDA, AVGO, ANET, etc.
We can infer this BEFORE filings by:
1. Analyzing earnings call transcripts for forward-looking language
2. Correlating sector moves with known fund themes
3. Tracking which stocks move together (factor exposure)

This module uses Perplexity to analyze recent earnings calls and extract signals.
"""
from __future__ import annotations
from dataclasses import dataclass
import requests
import json
import re


@dataclass
class EarningsInference:
    company: str
    ticker: str
    signal: str  # bullish_guidance, bearish_guidance, sector_theme, demand_acceleration, margin_pressure
    details: str
    likely_fund_interest: str  # which type of fund would care
    confidence: float


def analyze_recent_earnings(perplexity_api_key: str, tickers: list[str] | None = None) -> list[EarningsInference]:
    """Use Perplexity to analyze recent earnings calls for institutional signals."""
    if not perplexity_api_key:
        return []

    if tickers is None:
        tickers = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "JPM", "GS", "XOM", "CVX"]

    ticker_str = ", ".join(tickers)

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {perplexity_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar-finance",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an institutional equity analyst. Respond only with valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analyze the most recent earnings calls/guidance for these tickers: {ticker_str}. "
                            "For each company with recent earnings, identify: "
                            "1. Forward guidance tone (bullish/bearish/neutral) "
                            "2. Key themes mentioned (AI spend, margin expansion, demand, etc.) "
                            "3. Any language that suggests accelerating or decelerating business "
                            "4. Which type of institutional investors would be most interested "
                            'Respond as JSON: {{"earnings": [{{"ticker": "...", "signal": "bullish_guidance|bearish_guidance|neutral", '
                            '"details": "...", "themes": ["..."], "fund_interest": "growth|value|macro|quant"}}]}}'
                        ),
                    },
                ],
                "temperature": 0.1,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            return []

        data = json.loads(json_match.group())
        results = []

        for e in data.get("earnings", []):
            results.append(EarningsInference(
                company=e.get("ticker", ""),
                ticker=e.get("ticker", ""),
                signal=e.get("signal", "neutral"),
                details=e.get("details", ""),
                likely_fund_interest=e.get("fund_interest", ""),
                confidence=0.5 if e.get("signal") == "neutral" else 0.65,
            ))

        return results

    except Exception as e:
        print(f"Earnings inference error: {e}")
        return []
