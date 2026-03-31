"""FastAPI REST routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import load_config
from backend.db.database import (
    init_db, get_all_theses, get_all_predictions, get_chat_history,
    get_or_create_user_profile,
)
from backend.signals.scanner import SignalScanner
from backend.engine.causal_engine import CausalEngine
from backend.filings.tracker import FilingTracker
from backend.backtesting.backtester import Backtester
from backend.graph.thesis_graph import ThesisGraph
from backend.graph.trend_analyzer import analyze_thesis_trends
from backend.chat.agent import ChatAgent
from backend.chat.user_profile import UserProfileManager

router = APIRouter(prefix="/api")

# Lazy-loaded singletons
_config = None
_scanner = None
_engine = None
_filing_tracker = None
_backtester = None
_thesis_graph = None
_chat_agent = None


def _get_config():
    global _config
    if _config is None:
        _config = load_config()
        init_db(_config.db_path)
    return _config


def _get_scanner():
    global _scanner
    if _scanner is None:
        _scanner = SignalScanner(_get_config())
    return _scanner


def _get_engine():
    global _engine
    if _engine is None:
        _engine = CausalEngine(_get_config())
    return _engine


def _get_filing_tracker():
    global _filing_tracker
    if _filing_tracker is None:
        _filing_tracker = FilingTracker(_get_config())
    return _filing_tracker


def _get_backtester():
    global _backtester
    if _backtester is None:
        _backtester = Backtester(_get_config().db_path)
    return _backtester


def _get_thesis_graph():
    global _thesis_graph
    if _thesis_graph is None:
        _thesis_graph = ThesisGraph(_get_config())
    return _thesis_graph


def _get_chat_agent():
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent(_get_config())
    return _chat_agent


# --- Signal endpoints ---

@router.get("/signals")
async def get_signals():
    """Run all signal scanners and return current market state."""
    try:
        scanner = _get_scanner()
        report = scanner.scan_all()
        return {"status": "ok", "data": report.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Thesis endpoints ---

class ThesisRequest(BaseModel):
    query: str | None = None


@router.post("/theses/generate")
async def generate_theses(req: ThesisRequest):
    """Generate investment theses from current signals."""
    try:
        scanner = _get_scanner()
        signals = scanner.scan_all()
        engine = _get_engine()
        theses = engine.build_theses(signals.to_summary(), req.query)

        # Save to graph and backtester
        graph = _get_thesis_graph()
        bt = _get_backtester()
        for t in theses:
            graph.add_thesis(t.to_db_dict())
        bt.log_theses(theses)

        return {"status": "ok", "theses": [t.to_dict() for t in theses]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/theses")
async def list_theses():
    """List all stored theses."""
    config = _get_config()
    theses = get_all_theses(config.db_path)
    return {"status": "ok", "data": theses}


# --- Graph endpoints ---

@router.get("/graph")
async def get_graph():
    """Get thesis graph (nodes + edges) for visualization."""
    graph = _get_thesis_graph()
    return {"status": "ok", "data": graph.get_graph()}


@router.get("/graph/trends")
async def get_trends():
    """Get statistical trend analysis of the thesis graph."""
    config = _get_config()
    trends = analyze_thesis_trends(config.db_path)
    return {"status": "ok", "data": [{"type": t.insight_type, "title": t.title,
             "details": t.details, "recommendation": t.recommendation,
             "data": t.supporting_data} for t in trends]}


# --- Filing intelligence endpoints ---

@router.get("/filings")
async def get_filing_intel():
    """Run filing intelligence scan across all layers."""
    try:
        tracker = _get_filing_tracker()
        scanner = _get_scanner()
        signals = scanner.scan_all()
        report = tracker.run_full_scan(signals.to_summary())
        return {"status": "ok", "data": report.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Scorecard endpoints ---

@router.get("/scorecard")
async def get_scorecard():
    """Get prediction track record."""
    bt = _get_backtester()
    resolved = bt.check_outcomes()
    record = bt.get_track_record()
    return {"status": "ok", "track_record": record.to_dict(), "recently_resolved": resolved}


@router.get("/predictions")
async def list_predictions():
    """List all predictions."""
    config = _get_config()
    preds = get_all_predictions(config.db_path)
    return {"status": "ok", "data": preds}


# --- Chat endpoints ---

class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """Send a message to the chat agent."""
    try:
        agent = _get_chat_agent()
        # Get current market context for the agent
        try:
            scanner = _get_scanner()
            signals = scanner.scan_all()
            signal_summary = signals.to_summary()
        except Exception:
            signal_summary = ""

        response = agent.chat(req.message, signal_summary=signal_summary)
        return {"status": "ok", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history")
async def get_history():
    """Get chat history."""
    config = _get_config()
    history = get_chat_history(config.db_path, limit=50)
    return {"status": "ok", "data": history}


# --- User profile endpoints ---

class ProfileUpdate(BaseModel):
    risk_tolerance: str | None = None
    experience_level: str | None = None
    investment_horizon: str | None = None
    sectors_of_interest: list[str] | None = None
    portfolio_size: float | None = None


@router.get("/profile")
async def get_profile():
    """Get user profile."""
    config = _get_config()
    profile = UserProfileManager(config.db_path).get_profile()
    return {"status": "ok", "data": profile}


@router.put("/profile")
async def update_profile(req: ProfileUpdate):
    """Update user profile."""
    config = _get_config()
    pm = UserProfileManager(config.db_path)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    pm.update(**updates)
    return {"status": "ok", "data": pm.get_profile()}
