"""Statistical trend analyzer for the thesis graph.

Identifies meta-trends by analyzing:
1. Tag frequency over time (e.g., "3 of your last 5 theses involved semiconductors")
2. Connected thesis clusters (themes that keep recurring)
3. Accuracy patterns (which types of theses perform best)
4. Sector/factor concentration risks
"""
from __future__ import annotations
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.db.database import get_all_theses, get_thesis_edges, get_all_predictions


@dataclass
class TrendInsight:
    insight_type: str  # recurring_theme, cluster, accuracy_pattern, concentration_risk
    title: str
    details: str
    supporting_data: dict
    actionable: bool
    recommendation: str


def analyze_thesis_trends(db_path: str) -> list[TrendInsight]:
    """Analyze the thesis graph for meta-trends and patterns."""
    insights = []
    theses = get_all_theses(db_path)

    if len(theses) < 3:
        return [TrendInsight(
            insight_type="info",
            title="Building track record",
            details=f"Only {len(theses)} theses so far. Need at least 3 for trend analysis.",
            supporting_data={"count": len(theses)},
            actionable=False,
            recommendation="Keep generating theses to build your track record.",
        )]

    insights.extend(_analyze_tag_frequency(theses))
    insights.extend(_analyze_accuracy_patterns(db_path, theses))
    insights.extend(_analyze_concentration(theses))
    insights.extend(_analyze_thesis_clusters(db_path))

    return insights


def _analyze_tag_frequency(theses: list[dict]) -> list[TrendInsight]:
    """Find recurring themes in recent theses."""
    insights = []
    tag_counter = Counter()

    for t in theses[:20]:  # Last 20 theses
        tags = json.loads(t.get("tags_json", "[]"))
        for tag in tags:
            tag_counter[tag] += 1

    total = min(len(theses), 20)
    for tag, count in tag_counter.most_common(5):
        pct = count / total * 100
        if pct >= 40:  # Tag appears in 40%+ of recent theses
            insights.append(TrendInsight(
                insight_type="recurring_theme",
                title=f"Recurring theme: {tag}",
                details=f"'{tag}' appears in {count}/{total} ({pct:.0f}%) of your recent theses. "
                        f"This suggests a strong macro narrative you keep returning to.",
                supporting_data={"tag": tag, "count": count, "total": total, "pct": pct},
                actionable=True,
                recommendation=f"Consider whether your '{tag}' thesis is playing out as expected. "
                               f"If multiple theses share this theme, consolidation into fewer "
                               f"higher-conviction positions may be more capital-efficient.",
            ))

    return insights


def _analyze_accuracy_patterns(db_path: str, theses: list[dict]) -> list[TrendInsight]:
    """Find which types of theses perform best/worst."""
    insights = []
    predictions = get_all_predictions(db_path)

    if not predictions:
        return insights

    resolved = [p for p in predictions if p["outcome"] in ("WIN", "LOSS")]
    if len(resolved) < 5:
        return insights

    # Win rate by direction
    long_wins = sum(1 for p in resolved if p["direction"] == "LONG" and p["outcome"] == "WIN")
    long_total = sum(1 for p in resolved if p["direction"] == "LONG")
    short_wins = sum(1 for p in resolved if p["direction"] == "SHORT" and p["outcome"] == "WIN")
    short_total = sum(1 for p in resolved if p["direction"] == "SHORT")

    if long_total >= 3:
        long_wr = long_wins / long_total * 100
        if long_wr > 65:
            insights.append(TrendInsight(
                insight_type="accuracy_pattern",
                title="Strong long accuracy",
                details=f"Your LONG trades have a {long_wr:.0f}% win rate ({long_wins}/{long_total}). "
                        f"Consider sizing up on high-conviction longs.",
                supporting_data={"direction": "LONG", "wins": long_wins, "total": long_total, "win_rate": long_wr},
                actionable=True,
                recommendation="Your long thesis generation is performing well. Lean into it.",
            ))
        elif long_wr < 35:
            insights.append(TrendInsight(
                insight_type="accuracy_pattern",
                title="Weak long accuracy",
                details=f"Your LONG trades have a {long_wr:.0f}% win rate ({long_wins}/{long_total}). "
                        f"Consider reviewing your bullish thesis framework.",
                supporting_data={"direction": "LONG", "wins": long_wins, "total": long_total, "win_rate": long_wr},
                actionable=True,
                recommendation="Tighten entry criteria for long positions. Consider waiting for stronger confirmation signals.",
            ))

    if short_total >= 3:
        short_wr = short_wins / short_total * 100
        if short_wr < 35:
            insights.append(TrendInsight(
                insight_type="accuracy_pattern",
                title="Weak short accuracy",
                details=f"Your SHORT trades have a {short_wr:.0f}% win rate ({short_wins}/{short_total}).",
                supporting_data={"direction": "SHORT", "wins": short_wins, "total": short_total, "win_rate": short_wr},
                actionable=True,
                recommendation="Shorting is harder than going long. Consider using put spreads instead of outright shorts to limit risk.",
            ))

    # Overall win rate
    total_wr = len(resolved) and sum(1 for p in resolved if p["outcome"] == "WIN") / len(resolved) * 100
    insights.append(TrendInsight(
        insight_type="accuracy_pattern",
        title=f"Overall track record: {total_wr:.0f}% win rate",
        details=f"{sum(1 for p in resolved if p['outcome'] == 'WIN')}/{len(resolved)} predictions correct.",
        supporting_data={"total_resolved": len(resolved), "win_rate": total_wr},
        actionable=False,
        recommendation="",
    ))

    return insights


def _analyze_concentration(theses: list[dict]) -> list[TrendInsight]:
    """Check for over-concentration in specific tickers/sectors."""
    insights = []
    ticker_counter = Counter()

    for t in theses[:10]:
        tickers = json.loads(t.get("tickers_json", "[]"))
        for tk in tickers:
            if isinstance(tk, dict):
                ticker_counter[tk.get("ticker", "")] += 1
            elif isinstance(tk, str):
                ticker_counter[tk] += 1

    for ticker, count in ticker_counter.most_common(3):
        if count >= 3 and ticker:
            insights.append(TrendInsight(
                insight_type="concentration_risk",
                title=f"Concentration: {ticker}",
                details=f"{ticker} appears in {count} of your last 10 theses. "
                        f"You may be over-concentrated in this name.",
                supporting_data={"ticker": ticker, "count": count},
                actionable=True,
                recommendation=f"Review your total exposure to {ticker}. Consider whether multiple "
                               f"theses targeting the same ticker are truly independent bets or "
                               f"different expressions of the same underlying view.",
            ))

    return insights


def _analyze_thesis_clusters(db_path: str) -> list[TrendInsight]:
    """Find clusters of connected theses — themes that keep recurring."""
    insights = []
    edges = get_thesis_edges(db_path)

    if len(edges) < 3:
        return insights

    # Build adjacency count
    node_connections = Counter()
    for e in edges:
        node_connections[e["from_thesis_id"]] += 1
        node_connections[e["to_thesis_id"]] += 1

    # Find highly connected nodes (central theses)
    theses = {t["thesis_id"]: t for t in get_all_theses(db_path)}
    for thesis_id, conn_count in node_connections.most_common(3):
        if conn_count >= 3 and thesis_id in theses:
            t = theses[thesis_id]
            insights.append(TrendInsight(
                insight_type="cluster",
                title=f"Central thesis: {t['title'][:50]}",
                details=f"This thesis connects to {conn_count} other theses, making it a "
                        f"central node in your investment reasoning graph.",
                supporting_data={"thesis_id": thesis_id, "connections": conn_count},
                actionable=True,
                recommendation="This is a foundational thesis that drives many of your other views. "
                               "Pay close attention to catalysts that would confirm or invalidate it.",
            ))

    return insights
