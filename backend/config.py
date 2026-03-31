from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    # LLM
    anthropic_api_key: str = ""
    perplexity_api_key: str = ""

    # Data
    fred_api_key: str = ""
    finnhub_api_key: str = ""

    # Trading
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True

    # Delivery
    email_from: str = ""
    email_to: str = ""
    sendgrid_api_key: str = ""

    # Portfolio
    portfolio_size: float = 10000.0

    # Paths
    db_path: str = "situational.db"

    # Schedule
    schedule_time: str = "06:30"


def load_config() -> Config:
    load_dotenv()
    return Config(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        fred_api_key=os.getenv("FRED_API_KEY", ""),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY", ""),
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=True,
        email_from=os.getenv("EMAIL_FROM", ""),
        email_to=os.getenv("EMAIL_TO", ""),
        sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
        portfolio_size=float(os.getenv("PORTFOLIO_SIZE", "10000.0")),
        db_path=os.getenv("DB_PATH", "situational.db"),
        schedule_time=os.getenv("SCHEDULE_TIME", "06:30"),
    )
