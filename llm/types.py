"""Shared types for LLM providers."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str  # "user" | "assistant"
    content: str


class LLMClient(Protocol):
    def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        """Return assistant text. `messages` must end with a user message."""
        ...
