"""SEC EDGAR 13F filing parser.

13F-HR filings are required quarterly for institutional managers with $100M+ AUM.
They reveal equity holdings but with a ~45 day delay (filed 45 days after quarter end).

This is the BASELINE — we use this as ground truth to train our predictive models.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Holding:
    ticker: str
    cusip: str
    company_name: str
    shares: float
    value: float  # in USD
    filing_date: str
    report_date: str


@dataclass
class HoldingChange:
    ticker: str
    company_name: str
    change_type: str  # NEW, INCREASED, DECREASED, SOLD
    current_shares: float
    previous_shares: float
    current_value: float
    pct_change: float
    investor_name: str
    filing_date: str


# Pre-configured notable funds with CIK numbers
NOTABLE_FUNDS = {
    "berkshire_hathaway": {"name": "Berkshire Hathaway", "cik": "0001067983"},
    "bridgewater": {"name": "Bridgewater Associates", "cik": "0001350694"},
    "renaissance": {"name": "Renaissance Technologies", "cik": "0001037389"},
    "soros": {"name": "Soros Fund Management", "cik": "0001029160"},
    "pershing_square": {"name": "Pershing Square Capital", "cik": "0001336528"},
    "appaloosa": {"name": "Appaloosa Management", "cik": "0001656456"},
    "citadel": {"name": "Citadel Advisors", "cik": "0001423053"},
    "two_sigma": {"name": "Two Sigma Investments", "cik": "0001179392"},
    "de_shaw": {"name": "D.E. Shaw & Co", "cik": "0001009207"},
    "tiger_global": {"name": "Tiger Global Management", "cik": "0001167483"},
}


def get_fund_holdings(cik_or_name: str) -> list[Holding]:
    """Fetch latest 13F holdings for a fund. Uses edgartools."""
    try:
        from edgar import Company

        # Look up by name or CIK
        if cik_or_name in NOTABLE_FUNDS:
            name = NOTABLE_FUNDS[cik_or_name]["name"]
        else:
            name = cik_or_name

        company = Company(name)
        filings = company.get_filings(form="13F-HR")

        if not filings or len(filings) == 0:
            return []

        latest = filings[0]
        filing_obj = latest.obj()

        holdings = []
        if hasattr(filing_obj, 'infotable') and filing_obj.infotable is not None:
            df = filing_obj.infotable.to_dataframe()
            for _, row in df.iterrows():
                holdings.append(Holding(
                    ticker=str(row.get("ticker", row.get("cusip", "???"))),
                    cusip=str(row.get("cusip", "")),
                    company_name=str(row.get("nameOfIssuer", "")),
                    shares=float(row.get("shrsOrPrnAmt", {}).get("sshPrnamt", 0) if isinstance(row.get("shrsOrPrnAmt"), dict) else row.get("value", 0)),
                    value=float(row.get("value", 0)) * 1000,  # 13F reports in thousands
                    filing_date=str(latest.filing_date),
                    report_date=str(getattr(latest, 'period_of_report', latest.filing_date)),
                ))

        return holdings

    except Exception as e:
        logger.warning("13F parse error for %s: %s", cik_or_name, e)
        return []


def get_holding_changes(cik_or_name: str) -> list[HoldingChange]:
    """Compare last two 13F filings to detect changes."""
    try:
        from edgar import Company

        if cik_or_name in NOTABLE_FUNDS:
            info = NOTABLE_FUNDS[cik_or_name]
            name = info["name"]
        else:
            name = cik_or_name

        company = Company(name)
        filings = company.get_filings(form="13F-HR")

        if not filings or len(filings) < 2:
            return []

        def _parse_holdings(filing) -> dict[str, dict]:
            result = {}
            try:
                obj = filing.obj()
                if hasattr(obj, 'infotable') and obj.infotable is not None:
                    df = obj.infotable.to_dataframe()
                    for _, row in df.iterrows():
                        cusip = str(row.get("cusip", ""))
                        result[cusip] = {
                            "name": str(row.get("nameOfIssuer", "")),
                            "shares": float(row.get("shrsOrPrnAmt", {}).get("sshPrnamt", 0) if isinstance(row.get("shrsOrPrnAmt"), dict) else 0),
                            "value": float(row.get("value", 0)) * 1000,
                        }
            except Exception:
                pass
            return result

        current = _parse_holdings(filings[0])
        previous = _parse_holdings(filings[1])

        changes = []
        all_cusips = set(list(current.keys()) + list(previous.keys()))

        for cusip in all_cusips:
            curr = current.get(cusip)
            prev = previous.get(cusip)

            if curr and not prev:
                change_type = "NEW"
                pct = 100.0
                changes.append(HoldingChange(
                    ticker=cusip, company_name=curr["name"], change_type=change_type,
                    current_shares=curr["shares"], previous_shares=0,
                    current_value=curr["value"], pct_change=pct,
                    investor_name=name, filing_date=str(filings[0].filing_date),
                ))
            elif prev and not curr:
                changes.append(HoldingChange(
                    ticker=cusip, company_name=prev["name"], change_type="SOLD",
                    current_shares=0, previous_shares=prev["shares"],
                    current_value=0, pct_change=-100.0,
                    investor_name=name, filing_date=str(filings[0].filing_date),
                ))
            elif curr and prev and prev["shares"] > 0:
                pct = (curr["shares"] - prev["shares"]) / prev["shares"] * 100
                if pct > 5:
                    change_type = "INCREASED"
                elif pct < -5:
                    change_type = "DECREASED"
                else:
                    continue  # Skip unchanged
                changes.append(HoldingChange(
                    ticker=cusip, company_name=curr["name"], change_type=change_type,
                    current_shares=curr["shares"], previous_shares=prev["shares"],
                    current_value=curr["value"], pct_change=round(pct, 1),
                    investor_name=name, filing_date=str(filings[0].filing_date),
                ))

        # Sort by absolute value change
        changes.sort(key=lambda c: abs(c.pct_change), reverse=True)
        return changes[:20]  # Top 20 changes

    except Exception as e:
        logger.warning("13F change detection error for %s: %s", cik_or_name, e)
        return []
