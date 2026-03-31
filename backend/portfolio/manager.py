"""Portfolio manager — tracks user portfolio and notable investor portfolios."""
from __future__ import annotations
from dataclasses import dataclass

from backend.config import Config
from backend.db.database import save_tracked_portfolio, save_portfolio_holding
from backend.filings.edgar_13f import get_holding_changes, NOTABLE_FUNDS, HoldingChange


@dataclass
class PortfolioUpdate:
    investor_name: str
    changes: list[HoldingChange]
    total_changes: int


class PortfolioManager:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path

    def track_notable_investors(self) -> list[PortfolioUpdate]:
        """Check all tracked funds for portfolio changes."""
        updates = []

        for fund_key, fund_info in NOTABLE_FUNDS.items():
            try:
                changes = get_holding_changes(fund_key)
                if changes:
                    # Save to DB
                    portfolio_id = save_tracked_portfolio(
                        self.db_path, fund_info["name"], "hedge_fund", fund_info["cik"]
                    )
                    for change in changes[:10]:
                        save_portfolio_holding(
                            self.db_path, portfolio_id, change.ticker,
                            change.current_shares, change.current_value,
                            change.filing_date, change.change_type,
                        )

                    updates.append(PortfolioUpdate(
                        investor_name=fund_info["name"],
                        changes=changes[:10],
                        total_changes=len(changes),
                    ))
            except Exception as e:
                print(f"Error tracking {fund_info['name']}: {e}")
                continue

        return updates

    def get_notable_changes_summary(self) -> str:
        """Human-readable summary of notable investor changes."""
        updates = self.track_notable_investors()
        if not updates:
            return "No notable investor changes detected."

        lines = ["=== NOTABLE INVESTOR CHANGES ==="]
        for u in updates:
            lines.append(f"\n--- {u.investor_name} ({u.total_changes} changes) ---")
            for c in u.changes[:5]:
                lines.append(
                    f"  {c.change_type}: {c.company_name} ({c.ticker}) "
                    f"— {c.pct_change:+.1f}% ({c.current_shares:.0f} shares, ${c.current_value:,.0f})"
                )

        return "\n".join(lines)
