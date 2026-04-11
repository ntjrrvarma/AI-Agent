"""Google Gemini chat using google-generativeai."""

from __future__ import annotations

import google.generativeai as genai

from llm.types import ChatMessage


class GeminiClient:
    def __init__(self, api_key: str, model_name: str) -> None:
        genai.configure(api_key=api_key)
        self._model_name = model_name

    def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        if not messages:
            raise ValueError("messages must not be empty")
        if messages[-1]["role"] != "user":
            raise ValueError("messages must end with a user message")

        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_prompt,
        )

        history: list[dict] = []
        for msg in messages[:-1]:
            role = msg["role"]
            gemini_role = "model" if role == "assistant" else "user"
            history.append({"role": gemini_role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        text = response.text
        if text is None:
            return ""
        return text
