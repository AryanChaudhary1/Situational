"""Situation Room — Autonomous Retail Investment Agent.

FastAPI server + CLI orchestrator.

Usage:
  # Start API server
  python -m backend.main serve

  # Run full daily cycle
  python -m backend.main run

  # Manual thesis
  python -m backend.main thesis "yen carry trade unwinding"

  # Check scorecard
  python -m backend.main scorecard

  # Portfolio intelligence
  python -m backend.main portfolio

  # Start scheduled agent (6:30am ET daily)
  python -m backend.main schedule

  # Chat mode
  python -m backend.main chat
"""
from __future__ import annotations

import argparse
import sys
import asyncio
import logging
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)


async def run_daily_cycle(config):
    """Execute the full daily pipeline."""
    from backend.db.database import init_db, save_signal_snapshot
    from backend.signals.scanner import SignalScanner
    from backend.engine.causal_engine import CausalEngine
    from backend.filings.tracker import FilingTracker
    from backend.backtesting.backtester import Backtester
    from backend.graph.thesis_graph import ThesisGraph
    from backend.graph.trend_analyzer import analyze_thesis_trends
    from backend.reports.generator import ReportGenerator
    from backend.reports.delivery import deliver_report

    init_db(config.db_path)

    console.print("\n[bold cyan]SITUATION ROOM — Daily Cycle[/bold cyan]")
    console.print(f"[dim]{datetime.utcnow().isoformat()}[/dim]\n")

    # 1. Scan signals
    console.print("[yellow]Scanning market signals...[/yellow]")
    scanner = SignalScanner(config)
    signals = scanner.scan_all()
    save_signal_snapshot(config.db_path, "daily_scan", signals.to_dict())
    console.print(Panel(signals.to_summary()[:2000], title="Signal Report", border_style="cyan"))

    # 2. Check existing predictions
    console.print("[yellow]Checking open predictions...[/yellow]")
    bt = Backtester(config.db_path)
    resolved = bt.check_outcomes()
    if resolved:
        console.print(f"[green]Resolved {len(resolved)} predictions[/green]")
        for r in resolved:
            color = "green" if r["outcome"] == "WIN" else "red"
            console.print(f"  [{color}]{r['outcome']}[/{color}]: {r['ticker']} {r.get('return_pct', 0):+.1f}%")

    # 3. Filing intelligence
    console.print("[yellow]Running filing intelligence...[/yellow]")
    filing_tracker = FilingTracker(config)
    filing_report = filing_tracker.run_full_scan(signals.to_summary())
    if filing_report.flags:
        for f in filing_report.flags:
            console.print(f"  [bold red]! {f}[/bold red]")

    # 4. Build new theses
    console.print("[yellow]Generating investment theses...[/yellow]")
    engine = CausalEngine(config)
    theses = await engine.build_theses(signals.to_summary())

    # 5. Save to graph + log predictions
    graph = ThesisGraph(config)
    for t in theses:
        graph.add_thesis(t.to_db_dict())
        console.print(Panel(
            f"[bold]{t.title}[/bold]\n\n"
            f"{t.summary}\n\n"
            f"Confidence: {t.confidence:.0%} | Horizon: {t.time_horizon}\n"
            f"Tickers: {', '.join(r.ticker + ' ' + r.direction for r in t.tickers)}\n\n"
            f"Causal Chain:\n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(t.causal_chain)),
            title=f"Thesis: {t.title}",
            border_style="green",
        ))

    bt.log_theses(theses)

    # 6. Trend analysis
    trends = analyze_thesis_trends(config.db_path)
    if trends:
        console.print("\n[bold]Thesis Graph Trends:[/bold]")
        for trend in trends:
            console.print(f"  [{trend.insight_type}] {trend.title}: {trend.details[:100]}")

    # 7. Generate report
    console.print("[yellow]Generating report...[/yellow]")
    reporter = ReportGenerator(config)
    report_html = reporter.generate_daily_report(signals, theses, filing_report, bt.get_track_record())
    deliver_report(config, report_html, "daily")

    # 8. Track record
    record = bt.get_track_record()
    console.print(Panel(record.to_summary(), title="Track Record", border_style="magenta"))

    console.print("[bold green]Daily cycle complete.[/bold green]\n")


async def run_thesis(config, query: str):
    """Generate a thesis on a specific topic."""
    from backend.db.database import init_db
    from backend.signals.scanner import SignalScanner
    from backend.engine.causal_engine import CausalEngine
    from backend.graph.thesis_graph import ThesisGraph
    from backend.backtesting.backtester import Backtester

    init_db(config.db_path)

    console.print(f"\n[bold cyan]SITUATION ROOM — Thesis: {query}[/bold cyan]\n")

    scanner = SignalScanner(config)
    signals = scanner.scan_all()

    engine = CausalEngine(config)
    theses = await engine.build_theses(signals.to_summary(), manual_query=query)

    graph = ThesisGraph(config)
    bt = Backtester(config.db_path)

    for t in theses:
        t.source = "hybrid"  # User-prompted + agent-generated
        graph.add_thesis(t.to_db_dict())
        console.print(Panel(
            f"[bold]{t.title}[/bold]\n\n"
            f"{t.summary}\n\n"
            f"Confidence: {t.confidence:.0%} | Horizon: {t.time_horizon}\n\n"
            f"Causal Chain:\n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(t.causal_chain)) +
            f"\n\nRisks:\n" + "\n".join(f"  - {r}" for r in t.risks) +
            f"\n\nCatalysts:\n" + "\n".join(f"  - {c}" for c in t.catalysts) +
            f"\n\nTickers:\n" + "\n".join(
                f"  {r.ticker} {r.direction} | Entry: {r.entry_zone} | Target: {r.target} | Stop: {r.stop_loss}"
                for r in t.tickers
            ),
            title=f"Investment Thesis",
            border_style="green",
        ))

    bt.log_theses(theses)
    console.print(f"[dim]Logged {sum(len(t.tickers) for t in theses)} predictions to track record.[/dim]")


def run_scorecard(config):
    """Display the prediction track record."""
    from backend.db.database import init_db
    from backend.backtesting.backtester import Backtester

    init_db(config.db_path)
    bt = Backtester(config.db_path)
    bt.check_outcomes()
    record = bt.get_track_record()
    console.print(Panel(record.to_summary(), title="Track Record", border_style="magenta"))


def run_chat(config):
    """Interactive chat mode."""
    from backend.db.database import init_db
    from backend.chat.agent import ChatAgent
    from backend.signals.scanner import SignalScanner

    init_db(config.db_path)
    agent = ChatAgent(config)

    console.print("[bold cyan]SITUATION ROOM — Chat Mode[/bold cyan]")
    console.print("[dim]Type 'quit' to exit. The agent has access to live market signals.[/dim]\n")

    # Get initial signal context
    signal_summary = ""
    try:
        scanner = SignalScanner(config)
        signals = scanner.scan_all()
        signal_summary = signals.to_summary()
        console.print("[dim]Market context loaded.[/dim]\n")
    except Exception:
        console.print("[dim]Market context unavailable.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input.strip():
                continue

            response = agent.chat(user_input, signal_summary=signal_summary)
            console.print(f"\n[bold cyan]Situational:[/bold cyan] {response}\n")

        except (KeyboardInterrupt, EOFError):
            break

    console.print("\n[dim]Chat session ended.[/dim]")


def run_server(config, host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api.routes import router
    from backend.api.websocket import chat_websocket
    from backend.db.database import init_db

    init_db(config.db_path)

    app = FastAPI(title="Situation Room", description="Autonomous Retail Investment Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.websocket("/ws/chat")(chat_websocket)

    @app.get("/")
    async def root():
        return {"name": "Situation Room", "status": "running", "version": "0.1.0"}

    console.print(f"[bold cyan]Starting Situation Room API server on {host}:{port}[/bold cyan]")
    uvicorn.run(app, host=host, port=port)


def run_schedule(config):
    """Start the scheduler for daily runs."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    hour, minute = map(int, config.schedule_time.split(":"))
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_daily_cycle, 'cron',
        args=[config],
        hour=hour, minute=minute,
        timezone='US/Eastern',
    )

    console.print(f"[bold cyan]Scheduler started. Daily cycle at {config.schedule_time} ET.[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[dim]Scheduler stopped.[/dim]")


def main():
    from backend.config import load_config

    parser = argparse.ArgumentParser(description="Situation Room — Autonomous Investment Agent")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("run", help="Run full daily cycle")
    subparsers.add_parser("scorecard", help="Show prediction track record")
    subparsers.add_parser("portfolio", help="Show notable investor changes")
    subparsers.add_parser("chat", help="Interactive chat mode")
    subparsers.add_parser("schedule", help="Start daily scheduler")

    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    thesis_parser = subparsers.add_parser("thesis", help="Generate thesis on topic")
    thesis_parser.add_argument("query", help="The thesis topic or question")

    args = parser.parse_args()
    config = load_config()

    if args.command == "run":
        asyncio.run(run_daily_cycle(config))
    elif args.command == "thesis":
        asyncio.run(run_thesis(config, args.query))
    elif args.command == "scorecard":
        run_scorecard(config)
    elif args.command == "chat":
        run_chat(config)
    elif args.command == "serve":
        run_server(config, args.host, args.port)
    elif args.command == "schedule":
        run_schedule(config)
    elif args.command == "portfolio":
        from backend.db.database import init_db
        from backend.portfolio.manager import PortfolioManager
        init_db(config.db_path)
        pm = PortfolioManager(config)
        console.print(pm.get_notable_changes_summary())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
