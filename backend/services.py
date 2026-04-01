"""Service layer — single source of truth for all business logic.

Both the API routes and CLI call into these services. No business logic
should live in routes.py or main.py — only request parsing and presentation.

ServiceContainer holds all initialized modules and provides a clean
dependency injection point for testing (swap any component).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from backend.config import Config
from backend.db.database import (
    init_db, save_signal_snapshot, get_all_theses, get_all_predictions,
    get_chat_history,
)
from backend.signals.scanner import SignalScanner, SignalReport
from backend.engine.causal_engine import CausalEngine, InvestmentThesis
from backend.filings.tracker import FilingTracker, FilingIntelReport
from backend.backtesting.backtester import Backtester, TrackRecord
from backend.graph.thesis_graph import ThesisGraph
from backend.graph.trend_analyzer import analyze_thesis_trends, TrendInsight
from backend.chat.agent import ChatAgent
from backend.chat.user_profile import UserProfileManager
from backend.exceptions import SituationalError

logger = logging.getLogger(__name__)


@dataclass
class ThesisResult:
    """Result of thesis generation, with context about what was filtered."""
    theses: list[InvestmentThesis]
    predictions_logged: int
    tickers_validated: int
    tickers_filtered: int


@dataclass
class DailyCycleResult:
    """Result of a full daily cycle run."""
    signals: SignalReport
    resolved_predictions: list[dict]
    filing_report: FilingIntelReport
    thesis_result: ThesisResult
    trends: list[TrendInsight]
    track_record: TrackRecord


class ServiceContainer:
    """Holds all initialized service modules.

    Created once per application lifetime (server startup or CLI invocation).
    All modules share the same config and db_path, ensuring consistency.
    Thread safety: each module manages its own internal state. The container
    itself is read-only after construction.
    """

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path

        # Initialize database
        init_db(self.db_path)

        # Eagerly create lightweight modules, lazily create expensive ones
        self._scanner: SignalScanner | None = None
        self._engine: CausalEngine | None = None
        self._filing_tracker: FilingTracker | None = None
        self._backtester: Backtester | None = None
        self._thesis_graph: ThesisGraph | None = None
        self._chat_agent: ChatAgent | None = None
        self._profile_manager: UserProfileManager | None = None

    @property
    def scanner(self) -> SignalScanner:
        if self._scanner is None:
            self._scanner = SignalScanner(self.config)
        return self._scanner

    @property
    def engine(self) -> CausalEngine:
        if self._engine is None:
            self._engine = CausalEngine(self.config)
        return self._engine

    @property
    def filing_tracker(self) -> FilingTracker:
        if self._filing_tracker is None:
            self._filing_tracker = FilingTracker(self.config)
        return self._filing_tracker

    @property
    def backtester(self) -> Backtester:
        if self._backtester is None:
            self._backtester = Backtester(self.db_path)
        return self._backtester

    @property
    def thesis_graph(self) -> ThesisGraph:
        if self._thesis_graph is None:
            self._thesis_graph = ThesisGraph(self.config)
        return self._thesis_graph

    @property
    def chat_agent(self) -> ChatAgent:
        if self._chat_agent is None:
            self._chat_agent = ChatAgent(self.config)
        return self._chat_agent

    @property
    def profile_manager(self) -> UserProfileManager:
        if self._profile_manager is None:
            self._profile_manager = UserProfileManager(self.db_path)
        return self._profile_manager


# ---------------------------------------------------------------------------
# Service functions — the actual business logic
# ---------------------------------------------------------------------------

def scan_signals(container: ServiceContainer) -> SignalReport:
    """Scan all market signals (uses scanner's internal cache)."""
    return container.scanner.scan_all()


async def generate_theses(
    container: ServiceContainer,
    manual_query: str | None = None,
    source: str = "agent",
) -> ThesisResult:
    """Generate theses, save to graph, log predictions.

    This is the core pipeline that was previously duplicated in
    routes.py (POST /theses/generate) and main.py (run_daily_cycle, run_thesis).
    """
    signals = container.scanner.scan_all()
    theses = await container.engine.build_theses(signals.to_summary(), manual_query)

    if source != "agent":
        for t in theses:
            t.source = source

    # Save to graph
    for t in theses:
        container.thesis_graph.add_thesis(t.to_db_dict())

    # Log predictions
    container.backtester.log_theses(theses)

    total_tickers = sum(len(t.tickers) for t in theses)
    return ThesisResult(
        theses=theses,
        predictions_logged=total_tickers,
        tickers_validated=total_tickers,
        tickers_filtered=0,  # filtering happens inside CausalEngine
    )


def check_predictions(container: ServiceContainer) -> list[dict]:
    """Check open predictions against current prices, resolve where possible."""
    return container.backtester.check_outcomes()


def get_track_record(container: ServiceContainer) -> TrackRecord:
    """Get aggregate track record."""
    return container.backtester.get_track_record()


def scan_filings(container: ServiceContainer) -> FilingIntelReport:
    """Run full filing intelligence scan across all layers."""
    signals = container.scanner.scan_all()
    return container.filing_tracker.run_full_scan(signals.to_summary())


def get_graph_data(container: ServiceContainer) -> dict:
    """Get thesis graph nodes and edges for visualization."""
    return container.thesis_graph.get_graph()


def get_graph_trends(container: ServiceContainer) -> list[TrendInsight]:
    """Get statistical trend analysis of the thesis graph."""
    return analyze_thesis_trends(container.db_path)


def chat(container: ServiceContainer, message: str) -> str:
    """Send a message to the chat agent with market context.

    If signal scanning fails, the chat still works — just without
    market context. We log the failure instead of silently dropping it.
    """
    signal_summary = ""
    try:
        signals = container.scanner.scan_all()
        signal_summary = signals.to_summary()
    except Exception as e:
        logger.warning("Chat: market context unavailable: %s", e)

    return container.chat_agent.chat(message, signal_summary=signal_summary)


async def run_daily_cycle(container: ServiceContainer) -> DailyCycleResult:
    """Execute the full daily pipeline. Returns structured result.

    Callers (CLI, scheduler) handle presentation/formatting.
    """
    # 1. Scan signals
    signals = container.scanner.scan_all()
    save_signal_snapshot(container.db_path, "daily_scan", signals.to_dict())

    # 2. Check existing predictions
    resolved = container.backtester.check_outcomes()

    # 3. Filing intelligence
    filing_report = container.filing_tracker.run_full_scan(signals.to_summary())

    # 4. Generate theses (scan + reason + save + log)
    thesis_result = await generate_theses(container)

    # 5. Trend analysis
    trends = analyze_thesis_trends(container.db_path)

    # 6. Track record
    track_record = container.backtester.get_track_record()

    return DailyCycleResult(
        signals=signals,
        resolved_predictions=resolved,
        filing_report=filing_report,
        thesis_result=thesis_result,
        trends=trends,
        track_record=track_record,
    )
