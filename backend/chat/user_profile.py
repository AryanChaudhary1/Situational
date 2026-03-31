"""User profile management — preference learning over time."""
from __future__ import annotations
import json

from backend.db.database import get_or_create_user_profile, update_user_profile


class UserProfileManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_profile(self) -> dict:
        profile = get_or_create_user_profile(self.db_path)
        return {
            "risk_tolerance": profile.get("risk_tolerance", "moderate"),
            "sectors_of_interest": json.loads(profile.get("sectors_of_interest_json", "[]")),
            "investment_horizon": profile.get("investment_horizon", "medium"),
            "experience_level": profile.get("experience_level", "beginner"),
            "preferences": json.loads(profile.get("preferences_json", "{}")),
            "portfolio_size": profile.get("portfolio_size", 10000.0),
        }

    def get_profile_summary(self) -> str:
        p = self.get_profile()
        return (
            f"Risk Tolerance: {p['risk_tolerance']}\n"
            f"Experience Level: {p['experience_level']}\n"
            f"Investment Horizon: {p['investment_horizon']}\n"
            f"Sectors of Interest: {', '.join(p['sectors_of_interest']) or 'Not specified'}\n"
            f"Portfolio Size: ${p['portfolio_size']:,.0f}"
        )

    def update(self, **kwargs):
        if "sectors_of_interest" in kwargs:
            kwargs["sectors_of_interest_json"] = json.dumps(kwargs.pop("sectors_of_interest"))
        if "preferences" in kwargs:
            kwargs["preferences_json"] = json.dumps(kwargs.pop("preferences"))
        update_user_profile(self.db_path, **kwargs)
