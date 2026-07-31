"""Channel-neutral message/session lifecycle for the Agent framework."""
from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class ConversationRuntime:
    """Durable latest-turn-wins state, shared by CLI, Web and Feishu adapters."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, epoch INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS session_model_preferences "
                "(session_id TEXT PRIMARY KEY, model TEXT, updated_at REAL NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS session_context_summaries "
                "(session_id TEXT PRIMARY KEY, summary TEXT NOT NULL, source_turns INTEGER NOT NULL, updated_at REAL NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, source TEXT NOT NULL, delivery_id TEXT NOT NULL, "
                "session_id TEXT NOT NULL, epoch INTEGER NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL, "
                "created_at REAL NOT NULL, updated_at REAL NOT NULL, UNIQUE(source, delivery_id))"
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=3, isolation_level=None)
        db.execute("PRAGMA busy_timeout=3000")
        return db

    def accept(self, *, source: str, delivery_id: str, session_id: str, content: str) -> dict[str, Any]:
        """Accept a new logical turn and invalidate any older turn atomically."""
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT id, epoch, status FROM messages WHERE source=? AND delivery_id=?", (source, delivery_id)).fetchone()
            if existing:
                db.execute("COMMIT")
                return {"id": existing[0], "epoch": existing[1], "status": existing[2], "duplicate": True}
            row = db.execute("SELECT epoch FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            epoch = (row[0] if row else 0) + 1
            db.execute("INSERT INTO sessions(session_id, epoch, updated_at) VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET epoch=excluded.epoch, updated_at=excluded.updated_at", (session_id, epoch, now))
            db.execute("UPDATE messages SET status='superseded', updated_at=? WHERE session_id=? AND status IN ('accepted','running')", (now, session_id))
            message_id = "msg_" + uuid.uuid4().hex
            db.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, 'accepted', ?, ?)", (message_id, source, delivery_id, session_id, epoch, content, now, now))
            db.execute("COMMIT")
            return {"id": message_id, "epoch": epoch, "status": "accepted", "duplicate": False}

    def recover(self, *, source: str, delivery_id: str, session_id: str, content: str) -> dict[str, Any]:
        """Reclaim an accepted delivery after a process crash without duplicating it.

        A durable channel inbox may correctly requeue a message that was ACKed
        but never completed.  Plain ``accept`` would see that delivery ID and
        suppress it as a duplicate forever.  Recovery may only reclaim an
        unfinished record; completed/cancelled deliveries remain immutable.
        """
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id, status FROM messages WHERE source=? AND delivery_id=?",
                (source, delivery_id),
            ).fetchone()
            if not existing or existing[1] not in {"accepted", "running"}:
                db.execute("COMMIT")
                return self.accept(source=source, delivery_id=delivery_id, session_id=session_id, content=content)
            row = db.execute("SELECT epoch FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            epoch = (row[0] if row else 0) + 1
            db.execute(
                "INSERT INTO sessions(session_id, epoch, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET epoch=excluded.epoch, updated_at=excluded.updated_at",
                (session_id, epoch, now),
            )
            db.execute(
                "UPDATE messages SET status='superseded', updated_at=? WHERE session_id=? AND status IN ('accepted','running') AND id!=?",
                (now, session_id, existing[0]),
            )
            db.execute(
                "UPDATE messages SET session_id=?, epoch=?, content=?, status='accepted', updated_at=? WHERE id=?",
                (session_id, epoch, content, now, existing[0]),
            )
            db.execute("COMMIT")
            return {"id": existing[0], "epoch": epoch, "status": "accepted", "duplicate": False, "recovered": True}

    def is_current(self, session_id: str, epoch: int) -> bool:
        with self._db() as db:
            row = db.execute("SELECT epoch FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return bool(row and row[0] == epoch)

    def finish(self, message_id: str, status: str) -> None:
        with self._db() as db:
            db.execute("UPDATE messages SET status=?, updated_at=? WHERE id=?", (status, time.time(), message_id))

    def cancel_session(self, session_id: str) -> int:
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT epoch FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            epoch = (row[0] if row else 0) + 1
            db.execute("INSERT INTO sessions(session_id, epoch, updated_at) VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET epoch=excluded.epoch, updated_at=excluded.updated_at", (session_id, epoch, now))
            db.execute("UPDATE messages SET status='cancelled', updated_at=? WHERE session_id=? AND status IN ('accepted','running')", (now, session_id))
            db.execute("COMMIT")
        return epoch

    def get_model_preference(self, session_id: str) -> str | None:
        """Return the user-selected model for a session, or None for auto-routing."""
        with self._db() as db:
            row = db.execute(
                "SELECT model FROM session_model_preferences WHERE session_id=?", (session_id,)
            ).fetchone()
        return str(row[0]) if row and row[0] else None

    def set_model_preference(self, session_id: str, model: str | None) -> None:
        """Persist a session-only override without changing global configuration."""
        with self._db() as db:
            if model is None:
                db.execute("DELETE FROM session_model_preferences WHERE session_id=?", (session_id,))
            else:
                db.execute(
                    "INSERT INTO session_model_preferences(session_id, model, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(session_id) DO UPDATE SET model=excluded.model, updated_at=excluded.updated_at",
                    (session_id, model, time.time()),
                )

    def get_context_summary(self, session_id: str) -> str:
        with self._db() as db:
            row = db.execute(
                "SELECT summary FROM session_context_summaries WHERE session_id=?", (session_id,)
            ).fetchone()
        return str(row[0]) if row else ""

    def save_context_summary(self, session_id: str, summary: str, source_turns: int) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO session_context_summaries(session_id, summary, source_turns, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET summary=excluded.summary, source_turns=excluded.source_turns, updated_at=excluded.updated_at",
                (session_id, summary, source_turns, time.time()),
            )

    def clear_context_summary(self, session_id: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM session_context_summaries WHERE session_id=?", (session_id,))
