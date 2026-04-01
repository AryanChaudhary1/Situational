"""Situation Room — Autonomous Retail Investment Agent.

FastAPI server + CLI orchestrator.

Usage:
  python -m backend.main serve          # Start API server
  python -m backend.main run            # Run full daily cycle
  python -m backend.main thesis "query" # Manual thesis
  python -m backend.main scorecard      # Check scorecard
  python -m backend.main portfolio      # Portfolio intelligence
  python -m backend.main schedule       # Start scheduled agent (6:30am ET daily)
  python -m backend.main chat           # Chat mode
"""
from __future__ import annotations

import argparse
import sys
import asyncio
import logging
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from backend.config import load_config
from backend.services import (
    ServiceContainer,
    scan_signals,
    generate_theses,
    check_predictions,
    get_track_record,
    chat as service_chat,
    run_daily_cycle,
)

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI presentation helpers (format service results for terminal output)
# ---------------------------------------------------------------------------

def _print_thesis(t) -> None:
    """Pretty-print a single thesis to the console."""
    ticker_lines = "\n".join(
        f"  {r.ticker} {r.direction} | Entry: {r.entry_zone} | Target: {r.target} | Stop: {r.stop_loss}"
        for r in t.tickers
    )
    console.print(Panel(
        f"[bold]{t.title}[/bold]\n\n"
        f"{t.summary}\n\n"
        f"Confidence: {t.confidence:.0%} | Horizon: {t.time_horizon}\n\n"
        f"Causal Chain:\n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(t.causal_chain)) +
        f"\n\nRisks:\n" + "\n".join(f"  - {r}" for r in t.risks) +
        f"\n\nCatalysts:\n" + "\n".join(f"  - {c}" for c in t.catalysts) +
        f"\n\nTickers:\n{ticker_lines}",
        title="Investment Thesis",
        border_style="green",
    ))


def _print_resolved(resolved: list[dict]) -> None:
    """Print resolved predictions."""
    if not resolved:
        return
    console.print(f"[green]Resolved {len(resolved)} predictions[/green]")
    for r in resolved:
        color = "green" if r["outcome"] == "WIN" else "red"
        console.print(f"  [{color}]{r['outcome']}[/{color}]: {r['ticker']} {r.get('return_pct', 0):+.1f}%")


# ---------------------------------------------------------------------------
# CLI commands — each calls into the service layer, then formats output
# ---------------------------------------------------------------------------

async def cmd_run(container: ServiceContainer) -> None:
    """Run the full daily cycle."""
    console.print("\n[bold cyan]SITUATION ROOM — Daily Cycle[/bold cyan]")
    console.print(f"[dim]{datetime.utcnow().isoformat()}[/dim]\n")

    result = await run_daily_cycle(container)

    # Display signals
    console.print(Panel(result.signals.to_summary()[:2000], title="Signal Report", border_style="cyan"))

    # Display resolved predictions
    _print_resolved(result.resolved_predictions)

    # Display filing flags
    if result.filing_report.flags:
        for f in result.filing_report.flags:
            console.print(f"  [bold red]! {f}[/bold red]")

    # Display theses
    for t in result.thesis_result.theses:
        _print_thesis(t)

    # Display trends
    if result.trends:
        console.print("\n[bold]Thesis Graph Trends:[/bold]")
        for trend in result.trends:
            console.print(f"  [{trend.insight_type}] {trend.title}: {trend.details[:100]}")

    # Generate and deliver report
    from backend.reports.generator import ReportGenerator
    from backend.reports.delivery import deliver_report
    reporter = ReportGenerator(container.config)
    report_html = reporter.generate_daily_report(
        result.signals, result.thesis_result.theses,
        result.filing_report, result.track_record,
    )
    deliver_report(container.config, report_html, "daily")

    # Display track record
    console.print(Panel(result.track_record.to_summary(), title="Track Record", border_style="magenta"))
    console.print("[bold green]Daily cycle complete.[/bold green]\n")


async def cmd_thesis(container: ServiceContainer, query: str) -> None:
    """Generate a thesis on a specific topic."""
    console.print(f"\n[bold cyan]SITUATION ROOM — Thesis: {query}[/bold cyan]\n")

    result = await generate_theses(container, manual_query=query, source="hybrid")

    for t in result.theses:
        _print_thesis(t)

    console.print(f"[dim]Logged {result.predictions_logged} predictions to track record.[/dim]")


def cmd_scorecard(container: ServiceContainer) -> None:
    """Display the prediction track record."""
    check_predictions(container)
    record = get_track_record(container)
    console.print(Panel(record.to_summary(), title="Track Record", border_style="magenta"))


def cmd_chat(container: ServiceContainer) -> None:
    """Interactive chat mode."""
    console.print("[bold cyan]SITUATION ROOM — Chat Mode[/bold cyan]")
    console.print("[dim]Type 'quit' to exit. The agent has access to live market signals.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input.strip():
                continue

            response = service_chat(container, user_input)
            console.print(f"\n[bold cyan]Situational:[/bold cyan] {response}\n")

        except (KeyboardInterrupt, EOFError):
            break

    console.print("\n[dim]Chat session ended.[/dim]")


def cmd_portfolio(container: ServiceContainer) -> None:
    """Show notable investor changes."""
    from backend.portfolio.manager import PortfolioManager
    pm = PortfolioManager(container.config)
    console.print(pm.get_notable_changes_summary())


def cmd_serve(container: ServiceContainer, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI server."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api.routes import router
    from backend.api.websocket import chat_websocket

    app = FastAPI(title="Situation Room", description="Autonomous Retail Investment Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach the service container to app state — routes access it via request.app.state
    app.state.container = container

    app.include_router(router)
    app.websocket("/ws/chat")(chat_websocket)

    @app.get("/")
    async def root():
        return {"name": "Situation Room", "status": "running", "version": "0.2.0"}

    console.print(f"[bold cyan]Starting Situation Room API server on {host}:{port}[/bold cyan]")
    uvicorn.run(app, host=host, port=port)


def cmd_schedule(container: ServiceContainer) -> None:
    """Start the scheduler for daily runs."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    schedule_time = container.config.schedule_time
    try:
        hour, minute = map(int, schedule_time.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        logger.error("Invalid schedule_time '%s', expected HH:MM format", schedule_time)
        sys.exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: asyncio.run(run_daily_cycle(container)),
        "cron",
        hour=hour, minute=minute,
        timezone="US/Eastern",
    )

    console.print(f"[bold cyan]Scheduler started. Daily cycle at {schedule_time} ET.[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[dim]Scheduler stopped.[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
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

    # Single container for all commands
    container = ServiceContainer(config)

    if args.command == "run":
        asyncio.run(cmd_run(container))
    elif args.command == "thesis":
        asyncio.run(cmd_thesis(container, args.query))
    elif args.command == "scorecard":
        cmd_scorecard(container)
    elif args.command == "chat":
        cmd_chat(container)
    elif args.command == "serve":
        cmd_serve(container, args.host, args.port)
    elif args.command == "schedule":
        cmd_schedule(container)
    elif args.command == "portfolio":
        cmd_portfolio(container)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
