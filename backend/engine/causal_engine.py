"""Causal reasoning engine — the brain of Situational.

Two-pass architecture:
  Pass 1: Free-form macro reasoning (Claude thinks freely about signals)
  Pass 2: Structured JSON output with validated tickers

This mimics how a quant PM thinks: first understand the macro picture,
then translate into specific, executable trades.
"""
from __future__ import annotations

import json
import re
import uuid
import asyncio
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

import anthropic

logger = logging.getLogger(__name__)

from backend.config import Config
from backend.engine.prompts import (
    SYSTEM_PROMPT,
    SIGNAL_ANALYSIS_PROMPT,
    MANUAL_THESIS_PROMPT,
    HOLDING_ANALYSIS_PROMPT,
    THESIS_JSON_FORMAT,
)
from backend.engine.ticker_validator import validate_ticker, TickerInfo


@dataclass
class TickerRecommendation:
    ticker: str
    instrument_type: str
    direction: str
    rationale: str
    entry_zone: str
    target: str
    stop_loss: str
    position_size_pct: float
    validated: bool = False
    current_price: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvestmentThesis:
    thesis_id: str
    title: str
    summary: str
    causal_chain: list[str]
    tickers: list[TickerRecommendation]
    confidence: float
    time_horizon: str
    time_horizon_days: int
    risks: list[str]
    catalysts: list[str]
    tags: list[str] = field(default_factory=list)
    source: str = "agent"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tickers"] = [t.to_dict() for t in self.tickers]
        return d

    def to_db_dict(self) -> dict:
        return {
            "thesis_id": self.thesis_id,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "causal_chain": self.causal_chain,
            "tickers": [t.to_dict() for t in self.tickers],
            "confidence": self.confidence,
            "time_horizon": self.time_horizon,
            "risks": self.risks,
            "catalysts": self.catalysts,
            "tags": self.tags,
        }


@dataclass
class HoldingAnalysis:
    investor_name: str
    ticker: str
    likely_thesis: str
    macro_connection: str
    agree_disagree: str
    exit_signals: list[str]
    retail_recommendation: str


class CausalEngine:
    def __init__(self, config: Config):
        self.config = config
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required for CausalEngine")
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    async def build_theses(self, signal_summary: str, manual_query: str | None = None) -> list[InvestmentThesis]:
        """Two-pass thesis generation from signal data (optimized with parallel Claude calls)."""

        mode = "manual" if manual_query else "signal_analysis"
        logger.info(f"[BUILD_THESES] Starting {mode} mode")

        # Pass 1: Free-form reasoning
        if manual_query:
            user_prompt = MANUAL_THESIS_PROMPT.format(
                query=manual_query, signal_report=signal_summary
            )
        else:
            user_prompt = SIGNAL_ANALYSIS_PROMPT.format(signal_report=signal_summary)

        # Run Pass 1 and get reasoning
        logger.debug("[PASS1] Generating free-form reasoning...")
        reasoning = await self._call_claude(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=2048,  # Reduced from 4096
        )
        logger.debug(f"[PASS1] Reasoning generated ({len(reasoning)} chars)")

        # Pass 2: Structure into JSON with validated tickers (reduced tokens too)
        structured_prompt = (
            f"Based on your analysis below, now output the structured investment theses.\n\n"
            f"YOUR ANALYSIS:\n{reasoning}\n\n"
            f"{THESIS_JSON_FORMAT}"
        )

        logger.debug("[PASS2] Generating structured JSON...")
        json_response = await self._call_claude(
            system="You are a JSON formatting assistant. Output ONLY valid JSON, nothing else.",
            user=structured_prompt,
            max_tokens=1024,  # Reduced from 4096
        )
        logger.debug(f"[PASS2] JSON generated ({len(json_response)} chars)")

        theses = self._parse_theses(json_response)
        logger.info(f"[PARSE] Parsed {len(theses)} theses from JSON")

        # Validate tickers
        for i, thesis in enumerate(theses):
            initial_count = len(thesis.tickers)
            logger.debug(f"  Thesis {i}: {thesis.title} ({initial_count} tickers)")

            for rec in thesis.tickers:
                logger.debug(f"    Validating {rec.ticker}...")
                info = validate_ticker(rec.ticker)
                if info:
                    rec.validated = True
                    rec.current_price = info.price
                    logger.debug(f"      ✓ Valid: ${info.price}")
                else:
                    logger.warning(f"      ✗ Invalid ticker: {rec.ticker}")

            # Filter to only validated tickers
            thesis.tickers = [t for t in thesis.tickers if t.validated]
            final_count = len(thesis.tickers)
            if final_count < initial_count:
                logger.warning(f"  Thesis {i}: Filtered {initial_count} → {final_count} tickers")

        # Remove theses with no valid tickers
        initial_theses = len(theses)
        theses = [t for t in theses if t.tickers]
        if len(theses) < initial_theses:
            logger.warning(f"Removed {initial_theses - len(theses)} theses with no valid tickers")

        logger.info(f"[BUILD_THESES] Complete: {len(theses)} theses with {sum(len(t.tickers) for t in theses)} total predictions")
        return theses

    async def analyze_holding(self, investor_name: str, ticker: str, shares: float,
                              value: float, change_type: str, filing_date: str,
                              signal_summary: str) -> HoldingAnalysis:
        """Explain WHY a notable investor holds a position."""
        prompt = HOLDING_ANALYSIS_PROMPT.format(
            investor_name=investor_name,
            ticker=ticker,
            shares=shares,
            value=value,
            change_type=change_type,
            filing_date=filing_date,
            signal_report=signal_summary,
        )

        response = await self._call_claude(
            system=SYSTEM_PROMPT,
            user=prompt,
            max_tokens=2048,
        )

        # Parse free-form response into structured analysis
        return HoldingAnalysis(
            investor_name=investor_name,
            ticker=ticker,
            likely_thesis=response,
            macro_connection="",
            agree_disagree="",
            exit_signals=[],
            retail_recommendation="",
        )

    async def _call_claude(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Call Claude API asynchronously."""
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        )
        return response.content[0].text

    def _parse_theses(self, json_str: str) -> list[InvestmentThesis]:
        """Parse JSON response into InvestmentThesis objects."""
        # Extract JSON from response (might have markdown wrapping)
        json_match = re.search(r'\{[\s\S]*\}', json_str)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return []

        theses_data = data.get("theses", [])
        if not theses_data:
            return []

        theses = []
        for td in theses_data:
            tickers = []
            for tr in td.get("tickers", []):
                tickers.append(TickerRecommendation(
                    ticker=tr.get("ticker", ""),
                    instrument_type=tr.get("instrument_type", "stock"),
                    direction=tr.get("direction", "LONG"),
                    rationale=tr.get("rationale", ""),
                    entry_zone=tr.get("entry_zone", ""),
                    target=tr.get("target", ""),
                    stop_loss=tr.get("stop_loss", ""),
                    position_size_pct=float(tr.get("position_size_pct", 0.02)),
                ))

            theses.append(InvestmentThesis(
                thesis_id=str(uuid.uuid4()),
                title=td.get("title", "Untitled"),
                summary=td.get("summary", ""),
                causal_chain=td.get("causal_chain", []),
                tickers=tickers,
                confidence=float(td.get("confidence", 0.5)),
                time_horizon=td.get("time_horizon", "unknown"),
                time_horizon_days=int(td.get("time_horizon_days", 30)),
                risks=td.get("risks", []),
                catalysts=td.get("catalysts", []),
                tags=td.get("tags", []),
                source="agent",
            ))

        return theses
