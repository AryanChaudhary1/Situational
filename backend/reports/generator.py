"""Report generator — assembles HTML reports from signal data, theses, and track record."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from backend.config import Config
from backend.db.database import save_report


TEMPLATE_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    def generate_daily_report(self, signals, theses, filing_report, track_record) -> str:
        """Generate a full daily HTML report."""
        try:
            template = self.env.get_template("daily_report.html")
        except Exception:
            return self._fallback_report(signals, theses, filing_report, track_record)

        html = template.render(
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            signals=signals.to_dict() if hasattr(signals, 'to_dict') else {},
            signal_summary=signals.to_summary() if hasattr(signals, 'to_summary') else "",
            theses=[t.to_dict() for t in theses] if theses else [],
            filing_report=filing_report.to_dict() if hasattr(filing_report, 'to_dict') else {},
            filing_flags=filing_report.flags if hasattr(filing_report, 'flags') else [],
            track_record=track_record.to_dict() if hasattr(track_record, 'to_dict') else {},
        )

        save_report(self.config.db_path, "daily", html)
        return html

    def _fallback_report(self, signals, theses, filing_report, track_record) -> str:
        """Plain HTML fallback if template is missing."""
        theses_html = ""
        for t in (theses or []):
            tickers = ", ".join(f"{r.ticker} {r.direction}" for r in t.tickers)
            chain = "<br>".join(f"{i+1}. {s}" for i, s in enumerate(t.causal_chain))
            theses_html += f"""
            <div style="border:1px solid #333;padding:16px;margin:12px 0;border-radius:8px;background:#1a1a2e;">
                <h3 style="color:#00d4ff;">{t.title}</h3>
                <p>{t.summary}</p>
                <p><strong>Confidence:</strong> {t.confidence:.0%} | <strong>Horizon:</strong> {t.time_horizon}</p>
                <p><strong>Tickers:</strong> {tickers}</p>
                <p><strong>Causal Chain:</strong><br>{chain}</p>
            </div>"""

        signal_text = signals.to_summary() if hasattr(signals, 'to_summary') else "N/A"
        record_text = track_record.to_summary() if hasattr(track_record, 'to_summary') else "N/A"

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Situation Room — Daily Briefing</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; background: #0a0a1a; color: #e0e0e0; max-width: 800px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
h2 {{ color: #7b68ee; margin-top: 30px; }}
pre {{ background: #1a1a2e; padding: 16px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
.flag {{ color: #ff6b6b; font-weight: bold; }}
</style>
</head><body>
<h1>Situation Room — Daily Briefing</h1>
<p style="color:#888;">{datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>

<h2>Market Signals</h2>
<pre>{signal_text}</pre>

<h2>Investment Theses</h2>
{theses_html if theses_html else "<p>No theses generated.</p>"}

<h2>Track Record</h2>
<pre>{record_text}</pre>

<p style="color:#666;font-size:0.8em;margin-top:40px;">
This is not financial advice. Situation Room is an AI-powered research tool.
Always do your own due diligence before making investment decisions.
</p>
</body></html>"""

        save_report(self.config.db_path, "daily", html)
        return html
