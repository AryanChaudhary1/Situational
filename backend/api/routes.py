"""FastAPI REST routes.

Thin layer: parse requests, call service functions, return responses.
No business logic lives here.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.constants import CHAT_HISTORY_LIMIT
from backend.db.database import get_all_theses, get_all_predictions, get_chat_history
from backend.services import (
    ServiceContainer,
    scan_signals,
    generate_theses,
    check_predictions,
    get_track_record,
    scan_filings,
    get_graph_data,
    get_graph_trends,
    chat,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_container(request: Request) -> ServiceContainer:
    """Retrieve the ServiceContainer from app state.

    The container is attached to the FastAPI app at startup (in main.py).
    This replaces the 7 global singletons with a single, testable object.
    """
    container: ServiceContainer | None = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return container


# --- Signal endpoints ---

@router.get("/signals")
async def get_signals(request: Request):
    """Run all signal scanners and return current market state."""
    try:
        container = _get_container(request)
        report = scan_signals(container)
        return {"status": "ok", "data": report.to_dict()}
    except Exception as e:
        logger.exception("GET /signals failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Thesis endpoints ---

class ThesisRequest(BaseModel):
    query: str | None = None


@router.post("/theses/generate")
async def generate_theses_endpoint(req: ThesisRequest, request: Request):
    """Generate investment theses from current signals."""
    try:
        container = _get_container(request)
        result = await generate_theses(container, manual_query=req.query)
        return {
            "status": "ok",
            "theses": [t.to_dict() for t in result.theses],
            "predictions_logged": result.predictions_logged,
        }
    except Exception as e:
        logger.exception("POST /theses/generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/theses")
async def list_theses(request: Request):
    """List all stored theses."""
    container = _get_container(request)
    theses = get_all_theses(container.db_path)
    return {"status": "ok", "data": theses}


# --- Graph endpoints ---

@router.get("/graph")
async def get_graph(request: Request):
    """Get thesis graph (nodes + edges) for visualization."""
    container = _get_container(request)
    return {"status": "ok", "data": get_graph_data(container)}


@router.get("/graph/trends")
async def get_trends(request: Request):
    """Get statistical trend analysis of the thesis graph."""
    container = _get_container(request)
    trends = get_graph_trends(container)
    return {"status": "ok", "data": [
        {"type": t.insight_type, "title": t.title,
         "details": t.details, "recommendation": t.recommendation,
         "data": t.supporting_data}
        for t in trends
    ]}


# --- Filing intelligence endpoints ---

@router.get("/filings")
async def get_filing_intel(request: Request):
    """Run filing intelligence scan across all layers."""
    try:
        container = _get_container(request)
        report = scan_filings(container)
        return {"status": "ok", "data": report.to_dict()}
    except Exception as e:
        logger.exception("GET /filings failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Scorecard endpoints ---

@router.get("/scorecard")
async def get_scorecard(request: Request):
    """Get prediction track record."""
    container = _get_container(request)
    resolved = check_predictions(container)
    record = get_track_record(container)
    return {"status": "ok", "track_record": record.to_dict(), "recently_resolved": resolved}


@router.get("/predictions")
async def list_predictions(request: Request):
    """List all predictions."""
    container = _get_container(request)
    preds = get_all_predictions(container.db_path)
    return {"status": "ok", "data": preds}


# --- Chat endpoints ---

class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    """Send a message to the chat agent."""
    try:
        container = _get_container(request)
        response = chat(container, req.message)
        return {"status": "ok", "response": response}
    except Exception as e:
        logger.exception("POST /chat failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history")
async def get_history(request: Request):
    """Get chat history."""
    container = _get_container(request)
    history = get_chat_history(container.db_path, limit=CHAT_HISTORY_LIMIT)
    return {"status": "ok", "data": history}


# --- User profile endpoints ---

class ProfileUpdate(BaseModel):
    risk_tolerance: str | None = None
    experience_level: str | None = None
    investment_horizon: str | None = None
    sectors_of_interest: list[str] | None = None
    portfolio_size: float | None = None


@router.get("/profile")
async def get_profile(request: Request):
    """Get user profile."""
    container = _get_container(request)
    profile = container.profile_manager.get_profile()
    return {"status": "ok", "data": profile}


@router.put("/profile")
async def update_profile(req: ProfileUpdate, request: Request):
    """Update user profile."""
    container = _get_container(request)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    container.profile_manager.update(**updates)
    return {"status": "ok", "data": container.profile_manager.get_profile()}
