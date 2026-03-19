from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ConversationStore:
    def __init__(self, db_path: Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or data_dir / "chat_memory.db"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id, id)"
            )
            connection.commit()

    def create_conversation(self, title: str | None = None) -> dict[str, Any]:
        now = self._now_iso()
        conversation_id = str(uuid.uuid4())
        safe_title = self._normalize_title(title)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, safe_title, now, now),
            )
            connection.commit()

        return {
            "id": conversation_id,
            "title": safe_title,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COALESCE((
                           SELECT content
                           FROM messages m
                           WHERE m.conversation_id = c.id
                           ORDER BY m.id DESC
                           LIMIT 1
                       ), '') AS last_message_preview
                FROM conversations c
                ORDER BY c.updated_at DESC
                """
            ).fetchall()

        return [self._serialize_summary(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            conversation_row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

            if conversation_row is None:
                return None

            message_rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()

        return {
            "id": conversation_row["id"],
            "title": conversation_row["title"],
            "created_at": conversation_row["created_at"],
            "updated_at": conversation_row["updated_at"],
            "messages": [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in message_rows
            ],
        }

    def replace_messages(self, conversation_id: str, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        now = self._now_iso()
        title = self._title_from_messages(messages)

        with self._connect() as connection:
            conversation_exists = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()

            if conversation_exists is None:
                return None

            connection.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))

            if messages:
                connection.executemany(
                    """
                    INSERT INTO messages (conversation_id, role, content, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (conversation_id, message["role"], message["content"], now)
                        for message in messages
                    ],
                )

            connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, conversation_id),
            )
            connection.commit()

        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            connection.commit()
            return cursor.rowcount > 0

    def _serialize_summary(self, row: sqlite3.Row) -> dict[str, Any]:
        preview = (row["last_message_preview"] or "").strip()
        if len(preview) > 120:
            preview = f"{preview[:120].rstrip()}..."

        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_message_preview": preview,
        }

    def _title_from_messages(self, messages: list[dict[str, str]]) -> str:
        for message in messages:
            if message.get("role") == "user":
                return self._normalize_title(message.get("content"))
        return "Nova conversa"

    def _normalize_title(self, value: str | None) -> str:
        if not value:
            return "Nova conversa"

        compact = " ".join(str(value).split())
        if not compact:
            return "Nova conversa"
        if len(compact) > 60:
            return f"{compact[:60].rstrip()}..."
        return compact

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()
