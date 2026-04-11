"""OpenAI-compatible chat (LM Studio, Ollama compatibility server, etc.)."""

from __future__ import annotations

from openai import OpenAI

from llm.types import ChatMessage


class LocalOpenAIClient:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        payload: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        payload.extend(dict(m) for m in messages)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=payload,
            temperature=0.7,
        )
        choice = response.choices[0]
        content = choice.message.content
        if not content:
            return ""
        return content
