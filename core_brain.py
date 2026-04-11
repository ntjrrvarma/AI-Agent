"""Backward-compatible facade over `Agent` (legacy import path)."""

from __future__ import annotations

from typing import Any

from agent import Agent
from config import load_settings


class AgentBrain:
    def __init__(
        self, persona_name: str, system_prompt: str, skills: list[Any] | None = None
    ):
        """
        Initializes the agent (persona + base instructions).
        Optional `skills` list of Python callables is ignored in this template; use skills/SKILL.md instead.
        """
        settings = load_settings()
        self._agent = Agent(
            settings=settings,
            persona_name=persona_name,
            base_system_prompt=system_prompt,
            legacy_tools=skills,
        )

    def chat_loop(self) -> None:
        self._agent.run_chat_loop()
