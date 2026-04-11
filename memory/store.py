"""SQLite-backed transcript, summaries, and recent-window reads."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from llm.types import ChatMessage


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MessageRow:
    id: int
    role: str
    content: str


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages (conversation_id, id);

            CREATE TABLE IF NOT EXISTS memory_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                up_to_message_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_summaries_conversation
            ON memory_summaries (conversation_id, id);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def ensure_conversation(self, conversation_id: str | None, title: str = "") -> str:
        cid = conversation_id or str(uuid.uuid4())
        now = _utc_now()
        row = self._conn.execute(
            "SELECT id FROM conversations WHERE id = ?", (cid,)
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (cid, title or "Chat", now, now),
            )
            self._conn.commit()
        return cid

    def touch_conversation(self, conversation_id: str) -> None:
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_utc_now(), conversation_id),
        )
        self._conn.commit()

    def append_message(self, conversation_id: str, role: str, content: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, _utc_now()),
        )
        self._conn.commit()
        self.touch_conversation(conversation_id)
        return int(cur.lastrowid)

    def get_recent_messages(
        self, conversation_id: str, limit: int
    ) -> list[ChatMessage]:
        rows = self._conn.execute(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()
        out: list[ChatMessage] = []
        for r in reversed(rows):
            role = r["role"]
            if role not in ("user", "assistant"):
                continue
            out.append(ChatMessage(role=role, content=r["content"]))
        return out

    def get_latest_summary(self, conversation_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT summary_text FROM memory_summaries
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row["summary_text"])

    def save_summary(
        self, conversation_id: str, summary_text: str, up_to_message_id: int
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO memory_summaries (conversation_id, summary_text, up_to_message_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, summary_text, up_to_message_id, _utc_now()),
        )
        self._conn.commit()

    def max_summarized_message_id(self, conversation_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT MAX(up_to_message_id) AS m FROM memory_summaries
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if row is None or row["m"] is None:
            return 0
        return int(row["m"])

    def get_messages_for_summary_batch(
        self, conversation_id: str, after_id: int, limit: int
    ) -> list[MessageRow]:
        rows = self._conn.execute(
            """
            SELECT id, role, content FROM messages
            WHERE conversation_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (conversation_id, after_id, limit),
        ).fetchall()
        return [
            MessageRow(id=int(r["id"]), role=str(r["role"]), content=str(r["content"]))
            for r in rows
        ]
