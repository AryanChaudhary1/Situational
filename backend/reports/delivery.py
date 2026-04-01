"""Report delivery — email + file fallback."""
from __future__ import annotations
from datetime import datetime
import logging
from pathlib import Path

from backend.config import Config

logger = logging.getLogger(__name__)


def deliver_report(config: Config, html: str, report_type: str = "daily") -> str:
    """Deliver a report via email (if configured) and save to disk."""
    # Always save to disk
    output_dir = Path("reports_output")
    output_dir.mkdir(exist_ok=True)
    filename = f"{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = output_dir / filename
    filepath.write_text(html)

    # Try email delivery
    if config.sendgrid_api_key and config.email_to:
        try:
            _send_sendgrid(config, html, report_type)
            return f"Delivered via SendGrid + saved to {filepath}"
        except Exception as e:
            logger.warning("SendGrid delivery failed: %s", e)

    return f"Saved to {filepath}"


def _send_sendgrid(config: Config, html: str, report_type: str):
    """Send report via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    subject = f"Situation Room — {report_type.title()} Briefing ({datetime.utcnow().strftime('%Y-%m-%d')})"

    message = Mail(
        from_email=config.email_from or "situationroom@example.com",
        to_emails=config.email_to,
        subject=subject,
        html_content=html,
    )

    sg = SendGridAPIClient(config.sendgrid_api_key)
    sg.send(message)
