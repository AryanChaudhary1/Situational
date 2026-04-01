"""Conversational agent — the user-facing intelligence layer.

This agent:
1. Takes user messages (news, questions, thesis ideas)
2. Routes them through the appropriate backend modules
3. Learns user preferences over time
4. Explains everything in language calibrated to user's experience level
"""
from __future__ import annotations

import anthropic

from backend.config import Config
from backend.constants import LLM_MODEL
from backend.db.database import save_chat_message, get_chat_history
from backend.chat.prompts import CHAT_SYSTEM_PROMPT, CHAT_WITH_CONTEXT_PROMPT
from backend.chat.user_profile import UserProfileManager


class ChatAgent:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        self.profile_manager = UserProfileManager(config.db_path)
        if config.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        else:
            self.client = None

    def chat(self, user_message: str, signal_summary: str = "",
             filing_summary: str = "") -> str:
        """Process a user message and return agent response."""
        if not self.client:
            return "API key required for chat. Please set ANTHROPIC_API_KEY."

        # Save user message
        save_chat_message(self.db_path, "user", user_message)

        # Build system prompt with user profile
        profile_summary = self.profile_manager.get_profile_summary()
        system = CHAT_SYSTEM_PROMPT.format(user_profile=profile_summary)

        # Build conversation context
        history = get_chat_history(self.db_path, limit=20)
        messages = []
        for msg in history[:-1]:  # Exclude the message we just saved
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Build the current user message with market context
        if signal_summary or filing_summary:
            contextualized = CHAT_WITH_CONTEXT_PROMPT.format(
                signal_summary=signal_summary[:2000] if signal_summary else "Not available",
                filing_summary=filing_summary[:1000] if filing_summary else "Not available",
                user_message=user_message,
            )
        else:
            contextualized = user_message

        messages.append({"role": "user", "content": contextualized})

        # Call Claude
        response = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            system=system,
            messages=messages,
        )

        assistant_response = response.content[0].text

        # Save response
        save_chat_message(self.db_path, "assistant", assistant_response)

        return assistant_response

    def update_preferences(self, **kwargs):
        """Update user preferences based on chat interactions."""
        self.profile_manager.update(**kwargs)
