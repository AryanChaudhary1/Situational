"""Congressional trade tracking via Finnhub API."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class CongressTrade:
    politician: str
    party: str
    ticker: str
    transaction_type: str  # buy, sell
    amount_range: str  # e.g., "$1,001 - $15,000"
    disclosure_date: str
    transaction_date: str


def get_congressional_trades(finnhub_api_key: str, days_back: int = 30) -> list[CongressTrade]:
    """Fetch recent congressional stock trades."""
    if not finnhub_api_key:
        return []

    try:
        import finnhub
        client = finnhub.Client(api_key=finnhub_api_key)

        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

        trades = client.stock_congressional_trading(from_date=from_date, to_date=to_date)

        results = []
        for t in (trades or []):
            results.append(CongressTrade(
                politician=t.get("name", "Unknown"),
                party=t.get("party", ""),
                ticker=t.get("symbol", ""),
                transaction_type=t.get("transactionType", ""),
                amount_range=t.get("amountRange", ""),
                disclosure_date=t.get("disclosureDate", ""),
                transaction_date=t.get("transactionDate", ""),
            ))

        return results

    except Exception as e:
        logger.warning("Congressional trades error: %s", e)
        return []
