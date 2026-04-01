from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.constants import DEFAULT_THESIS_CONFIDENCE, DEFAULT_EDGE_STRENGTH


SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db(db_path: str) -> str:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
    return db_path


@contextmanager
def _connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- Signal snapshots ---

def save_signal_snapshot(db_path: str, signal_type: str, data: dict) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO signal_snapshots (signal_type, data_json) VALUES (?, ?)",
            (signal_type, json.dumps(data, default=str)),
        )
        return cur.lastrowid


# --- Predictions ---

def save_prediction(db_path: str, thesis_id: str, ticker: str, direction: str,
                    entry_price: float, target_price: float, stop_price: float,
                    confidence: float, thesis_summary: str, time_horizon_days: int) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO predictions
               (thesis_id, ticker, direction, entry_price, target_price, stop_price,
                confidence, thesis_summary, time_horizon_days, outcome)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')""",
            (thesis_id, ticker, direction, entry_price, target_price, stop_price,
             confidence, thesis_summary, time_horizon_days),
        )
        return cur.lastrowid


def get_open_predictions(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE outcome = 'OPEN' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_prediction(db_path: str, prediction_id: int, exit_price: float, outcome: str):
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE predictions SET resolved_at = ?, exit_price = ?, outcome = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), exit_price, outcome, prediction_id),
        )


def get_all_predictions(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM predictions ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# --- Theses (graph nodes) ---

def save_thesis(db_path: str, thesis: dict) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO theses
               (thesis_id, source, title, summary, causal_chain_json, tickers_json,
                confidence, time_horizon, risks_json, catalysts_json, tags_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (thesis["thesis_id"], thesis.get("source", "agent"), thesis["title"],
             thesis.get("summary", ""), json.dumps(thesis.get("causal_chain", [])),
             json.dumps(thesis.get("tickers", [])), thesis.get("confidence", DEFAULT_THESIS_CONFIDENCE),
             thesis.get("time_horizon", ""), json.dumps(thesis.get("risks", [])),
             json.dumps(thesis.get("catalysts", [])), json.dumps(thesis.get("tags", []))),
        )
        return cur.lastrowid


def save_thesis_edge(db_path: str, from_id: str, to_id: str, relationship: str, strength: float = DEFAULT_EDGE_STRENGTH):
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO thesis_edges (from_thesis_id, to_thesis_id, relationship, strength) VALUES (?, ?, ?, ?)",
            (from_id, to_id, relationship, strength),
        )


def get_all_theses(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM theses ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_thesis_edges(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM thesis_edges ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# --- Filing signals ---

def save_filing_signal(db_path: str, signal_layer: str, source: str, investor_name: str,
                       ticker: str, signal_type: str, confidence: float,
                       details: dict, is_predictive: bool = False) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO filing_signals
               (signal_layer, source, investor_name, ticker, signal_type, confidence, details_json, is_predictive)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (signal_layer, source, investor_name, ticker, signal_type, confidence,
             json.dumps(details, default=str), is_predictive),
        )
        return cur.lastrowid


# --- User profiles ---

def get_or_create_user_profile(db_path: str) -> dict:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM user_profiles ORDER BY id LIMIT 1").fetchone()
        if row:
            return dict(row)
        conn.execute("INSERT INTO user_profiles DEFAULT VALUES")
        row = conn.execute("SELECT * FROM user_profiles ORDER BY id LIMIT 1").fetchone()
        return dict(row)


def update_user_profile(db_path: str, **kwargs):
    allowed = {"risk_tolerance", "sectors_of_interest_json", "investment_horizon",
               "experience_level", "preferences_json", "portfolio_size"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE user_profiles SET {set_clause}, updated_at = ? WHERE id = 1",
            (*updates.values(), datetime.utcnow().isoformat()),
        )


# --- Chat history ---

def save_chat_message(db_path: str, role: str, content: str, metadata: dict | None = None) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO chat_history (role, content, metadata_json) VALUES (?, ?, ?)",
            (role, content, json.dumps(metadata or {})),
        )
        return cur.lastrowid


def get_chat_history(db_path: str, limit: int = 50) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


# --- Reports ---

def save_report(db_path: str, report_type: str, content_html: str, content_text: str = "") -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO reports (report_type, content_html, content_text) VALUES (?, ?, ?)",
            (report_type, content_html, content_text),
        )
        return cur.lastrowid


# --- Portfolio tracking ---

def save_tracked_portfolio(db_path: str, name: str, investor_type: str, cik: str = "") -> int:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM tracked_portfolios WHERE investor_name = ?", (name,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO tracked_portfolios (investor_name, investor_type, cik) VALUES (?, ?, ?)",
            (name, investor_type, cik),
        )
        return cur.lastrowid


def save_portfolio_holding(db_path: str, portfolio_id: int, ticker: str, shares: float,
                           value: float, filing_date: str, change_type: str, cusip: str = "") -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO portfolio_holdings
               (portfolio_id, ticker, cusip, shares, value, filing_date, change_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (portfolio_id, ticker, cusip, shares, value, filing_date, change_type),
        )
        return cur.lastrowid
