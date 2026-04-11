"""Select and switch between local OpenAI-compatible and Gemini backends."""

from __future__ import annotations

from llm.gemini_client import GeminiClient
from llm.local_openai import LocalOpenAIClient
from llm.types import ChatMessage, LLMClient

from config import Settings


def _openai_base_url(url: str) -> str:
    u = url.rstrip("/")
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


class LLMRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._active_name = settings.primary_provider
        base = _openai_base_url(settings.openai_base_url)

        self._local = LocalOpenAIClient(
            base_url=base,
            api_key=settings.openai_api_key,
            model=settings.local_model,
        )
        self._gemini: GeminiClient | None = None
        if settings.gemini_api_key:
            self._gemini = GeminiClient(
                api_key=settings.gemini_api_key,
                model_name=settings.gemini_model,
            )

    @property
    def active_name(self) -> str:
        return self._active_name

    def _client(self) -> LLMClient:
        if self._active_name == "gemini":
            if self._gemini is None:
                raise RuntimeError(
                    "Gemini provider selected but GEMINI_API_KEY is not set."
                )
            return self._gemini
        return self._local

    def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        return self._client().complete(system_prompt, messages)

    def switch(self, name: str) -> None:
        normalized = name.strip().lower()
        if normalized not in ("local", "gemini"):
            raise ValueError("Provider must be 'local' or 'gemini'.")
        if normalized == "gemini" and self._gemini is None:
            raise RuntimeError("GEMINI_API_KEY is not set; cannot switch to Gemini.")
        self._active_name = normalized
