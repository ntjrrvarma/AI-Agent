"""Orchestration: system prompt (persona + skills + summaries), LLM router, SQLite memory."""

from __future__ import annotations

import os
from typing import Any

from config import Settings, load_settings
from llm.router import LLMRouter
from llm.types import ChatMessage
from memory.store import MemoryStore
from skills.loader import build_skills_index


class Agent:
    def __init__(
        self,
        *,
        settings: Settings,
        persona_name: str,
        base_system_prompt: str,
        conversation_id: str | None = None,
        legacy_tools: list[Any] | None = None,
    ) -> None:
        self._settings = settings
        self._persona = persona_name
        self._base_prompt = base_system_prompt
        self._router = LLMRouter(settings)
        self._memory = MemoryStore(settings.database_path)
        self._conversation_id = self._memory.ensure_conversation(
            conversation_id or os.environ.get("CONVERSATION_ID"),
            title=persona_name,
        )
        self._skills_index = build_skills_index(settings.skills_dir)
        if legacy_tools:
            print(
                f"[{persona_name}] Note: Python callable tools are not wired in this template; "
                f"received {len(legacy_tools)} ignored tool(s)."
            )

    @property
    def router(self) -> LLMRouter:
        return self._router

    @classmethod
    def from_defaults(cls, conversation_id: str | None = None) -> Agent:
        settings = load_settings()
        name = os.environ.get("AGENT_NAME", "Assistant")
        prompt = os.environ.get(
            "SYSTEM_PROMPT",
            "You are a concise, accurate assistant. Prefer short answers unless detail is requested.",
        )
        return cls(
            settings=settings,
            persona_name=name,
            base_system_prompt=prompt,
            conversation_id=conversation_id,
        )

    def _build_system_prompt(self) -> str:
        summary = self._memory.get_latest_summary(self._conversation_id)
        parts = [
            f"You are {self._persona}.",
            self._base_prompt,
            "",
            self._skills_index,
        ]
        if summary:
            parts.extend(
                [
                    "",
                    "## Compressed prior context (summary)",
                    summary,
                ]
            )
        return "\n".join(parts)

    def _maybe_summarize(self) -> None:
        after = self._memory.max_summarized_message_id(self._conversation_id)
        n = self._settings.summarize_every_n_messages
        batch = self._memory.get_messages_for_summary_batch(
            self._conversation_id, after, n
        )
        if len(batch) < n:
            return
        lines: list[str] = []
        for m in batch:
            if m.role not in ("user", "assistant"):
                continue
            lines.append(f"{m.role.upper()}: {m.content}")
        transcript = "\n".join(lines)
        summarizer_system = (
            "You compress chat transcripts into a concise factual summary for future context. "
            "Preserve names, decisions, open tasks, preferences, and key facts. "
            "Use short bullet points. No introduction."
        )
        summarizer_user = f"Summarize this chat segment:\n\n{transcript}"
        summary_text = self._router.complete(
            summarizer_system,
            [ChatMessage(role="user", content=summarizer_user)],
        )
        self._memory.save_summary(
            self._conversation_id, summary_text.strip(), batch[-1].id
        )

    def run_chat_loop(self) -> None:
        print("==================================================")
        print(f"TALKING TO: {self._persona} | provider={self._router.active_name}")
        print("Commands: exit | quit | switch | use local | use gemini | show summary")
        print("==================================================\n")

        while True:
            user_input = input("You: ").strip()
            lower = user_input.lower()

            if lower in ("exit", "quit"):
                print(f"[{self._persona}] Goodbye.")
                break

            if lower == "switch":
                try:
                    self._router.switch(
                        "gemini" if self._router.active_name == "local" else "local"
                    )
                    print(f"Provider: {self._router.active_name}")
                except (RuntimeError, ValueError) as e:
                    print(e)
                continue

            if lower == "use local":
                try:
                    self._router.switch("local")
                    print("Provider: local")
                except (RuntimeError, ValueError) as e:
                    print(e)
                continue

            if lower == "use gemini":
                try:
                    self._router.switch("gemini")
                    print("Provider: gemini")
                except (RuntimeError, ValueError) as e:
                    print(e)
                continue

            if lower == "show summary":
                s = self._memory.get_latest_summary(self._conversation_id)
                print("\n[Latest stored summary]\n", s or "(none yet)\n")
                continue

            if not user_input:
                continue

            self._memory.append_message(self._conversation_id, "user", user_input)
            messages = self._memory.get_recent_messages(
                self._conversation_id, self._settings.recent_messages_limit
            )
            if not messages or messages[-1]["role"] != "user":
                continue

            try:
                reply = self._router.complete(self._build_system_prompt(), messages)
            except Exception as e:
                print(f"\n[{self._persona} SYSTEM FAULT]: {e}\n")
                continue

            print(f"\n{self._persona}: {reply}\n")
            self._memory.append_message(self._conversation_id, "assistant", reply)
            try:
                self._maybe_summarize()
            except Exception as e:
                print(f"[memory compaction skipped: {e}]")
