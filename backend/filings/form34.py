"""Form 3/4 insider transaction parser — FASTEST filing signal.

Form 3: Initial statement of beneficial ownership (when someone becomes an insider).
Form 4: Changes in beneficial ownership — filed within 2 BUSINESS DAYS.

Form 4 is the gold standard for timely insider activity. When a CEO buys $5M of
their own stock, that Form 4 hits EDGAR within 2 days. Compare to 13F at 45 days.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class InsiderTransaction:
    insider_name: str
    insider_title: str  # CEO, CFO, Director, 10% Owner, etc.
    company: str
    ticker: str
    transaction_type: str  # BUY, SELL, OPTION_EXERCISE, GIFT
    shares: float
    price_per_share: float
    total_value: float
    shares_owned_after: float
    filing_date: str
    transaction_date: str
    is_direct: bool  # direct vs indirect ownership


def get_recent_insider_transactions(days_back: int = 14) -> list[InsiderTransaction]:
    """Fetch recent Form 3/4 filings from EDGAR."""
    try:
        from edgar import get_filings

        results = []
        for form_type in ["4", "3"]:
            filings = get_filings(form=form_type, recent_count=100)
            if not filings:
                continue

            for f in filings:
                try:
                    results.append(InsiderTransaction(
                        insider_name=str(getattr(f, 'filer', 'Unknown')),
                        insider_title="",
                        company=str(getattr(f, 'company_name', '')),
                        ticker="",  # Resolve from company name
                        transaction_type="UNKNOWN",
                        shares=0,
                        price_per_share=0,
                        total_value=0,
                        shares_owned_after=0,
                        filing_date=str(getattr(f, 'filing_date', '')),
                        transaction_date="",
                        is_direct=True,
                    ))
                except Exception:
                    continue

        return results

    except Exception as e:
        print(f"Form 3/4 fetch error: {e}")
        return []


def get_insider_transactions_for_ticker(ticker: str) -> list[InsiderTransaction]:
    """Get insider transactions for a specific ticker using yfinance as primary source."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        transactions = []

        # yfinance provides insider transactions directly
        insider_tx = t.insider_transactions
        if insider_tx is not None and not insider_tx.empty:
            for _, row in insider_tx.iterrows():
                tx_type = str(row.get("Transaction", "")).upper()
                if "PURCHASE" in tx_type or "BUY" in tx_type:
                    tx_type = "BUY"
                elif "SALE" in tx_type or "SELL" in tx_type:
                    tx_type = "SELL"
                elif "OPTION" in tx_type or "EXERCISE" in tx_type:
                    tx_type = "OPTION_EXERCISE"
                else:
                    tx_type = "OTHER"

                shares = abs(float(row.get("Shares", 0)))
                value = abs(float(row.get("Value", 0)))
                price = value / shares if shares > 0 else 0

                transactions.append(InsiderTransaction(
                    insider_name=str(row.get("Insider", "Unknown")),
                    insider_title=str(row.get("Position", "")),
                    company=ticker,
                    ticker=ticker,
                    transaction_type=tx_type,
                    shares=shares,
                    price_per_share=round(price, 2),
                    total_value=value,
                    shares_owned_after=float(row.get("Shares Held", 0)),
                    filing_date=str(row.get("Date", "")),
                    transaction_date=str(row.get("Date", "")),
                    is_direct=True,
                ))

        return transactions

    except Exception as e:
        print(f"Insider tx fetch error for {ticker}: {e}")
        return []
