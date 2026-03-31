"""Thesis graph — tracks all theses over time as a connected graph.

Nodes = theses (agent-generated or user-generated)
Edges = causal connections between theses

This builds a living knowledge graph of investment reasoning that the agent
learns from over time. When a new thesis is generated, we automatically
detect connections to previous theses and link them.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

from backend.config import Config
from backend.db.database import (
    save_thesis, save_thesis_edge, get_all_theses, get_thesis_edges,
)
from backend.engine.prompts import THESIS_CONNECTION_PROMPT


@dataclass
class ThesisNode:
    thesis_id: str
    title: str
    summary: str
    source: str  # agent, user, hybrid
    tags: list[str]
    confidence: float
    created_at: str
    outcome_score: float | None = None  # filled by backtester

    def to_dict(self) -> dict:
        return {
            "id": self.thesis_id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "tags": self.tags,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "outcome_score": self.outcome_score,
        }


@dataclass
class ThesisEdge:
    from_id: str
    to_id: str
    relationship: str
    strength: float

    def to_dict(self) -> dict:
        return {
            "source": self.from_id,
            "target": self.to_id,
            "relationship": self.relationship,
            "strength": self.strength,
        }


class ThesisGraph:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        if config.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        else:
            self.client = None

    def add_thesis(self, thesis_dict: dict) -> str:
        """Add a thesis node to the graph and auto-detect connections."""
        save_thesis(self.db_path, thesis_dict)

        # Auto-detect connections to recent theses
        if self.client:
            self._auto_connect(thesis_dict)

        return thesis_dict["thesis_id"]

    def get_graph(self) -> dict:
        """Return full graph as {nodes: [...], edges: [...]} for visualization."""
        raw_theses = get_all_theses(self.db_path)
        raw_edges = get_thesis_edges(self.db_path)

        nodes = []
        for t in raw_theses:
            nodes.append(ThesisNode(
                thesis_id=t["thesis_id"],
                title=t["title"],
                summary=t.get("summary", ""),
                source=t["source"],
                tags=json.loads(t.get("tags_json", "[]")),
                confidence=t.get("confidence", 0.5),
                created_at=t.get("created_at", ""),
                outcome_score=t.get("outcome_score"),
            ).to_dict())

        edges = []
        for e in raw_edges:
            edges.append(ThesisEdge(
                from_id=e["from_thesis_id"],
                to_id=e["to_thesis_id"],
                relationship=e["relationship"],
                strength=e.get("strength", 0.5),
            ).to_dict())

        return {"nodes": nodes, "edges": edges}

    def _auto_connect(self, new_thesis: dict):
        """Use Claude to detect connections between the new thesis and recent ones."""
        recent = get_all_theses(self.db_path)
        # Check against last 10 theses (skip self)
        candidates = [t for t in recent if t["thesis_id"] != new_thesis["thesis_id"]][:10]

        for candidate in candidates:
            try:
                prompt = THESIS_CONNECTION_PROMPT.format(
                    thesis_a_title=new_thesis["title"],
                    thesis_a_summary=new_thesis.get("summary", ""),
                    thesis_a_chain=json.dumps(new_thesis.get("causal_chain", [])),
                    thesis_b_title=candidate["title"],
                    thesis_b_summary=candidate.get("summary", ""),
                    thesis_b_chain=candidate.get("causal_chain_json", "[]"),
                )

                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=256,
                    system="Respond only with valid JSON.",
                    messages=[{"role": "user", "content": prompt}],
                )

                content = response.content[0].text
                json_match = re.search(r'\{[\s\S]*?\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                    if data.get("connected"):
                        save_thesis_edge(
                            self.db_path,
                            new_thesis["thesis_id"],
                            candidate["thesis_id"],
                            data.get("relationship", "related"),
                            float(data.get("strength", 0.5)),
                        )
            except Exception:
                continue  # Don't fail the whole pipeline for connection detection
