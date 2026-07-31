"""Channel-neutral durable outbound message state for the Agent framework."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class OutboxStore:
    """Persist reply delivery independently of any chat-channel SDK.

    Channel adapters own the last network hop.  This store owns idempotency,
    retry scheduling, cancellation and restart recovery for the logical reply.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS outbox_messages ("
                "id TEXT PRIMARY KEY, delivery_key TEXT NOT NULL UNIQUE, session_id TEXT NOT NULL, "
                "epoch INTEGER NOT NULL, channel TEXT NOT NULL, target TEXT NOT NULL, "
                "payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, "
                "next_attempt_at REAL NOT NULL, external_id TEXT, last_error TEXT, "
                "created_at REAL NOT NULL, updated_at REAL NOT NULL)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_outbox_due ON outbox_messages(status, next_attempt_at)")

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=3, isolation_level=None)
        db.execute("PRAGMA busy_timeout=3000")
        return db

    def enqueue(self, *, delivery_key: str, session_id: str, epoch: int, channel: str,
                target: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create one logical delivery, or update its unsent payload in place."""
        now = time.time()
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id, status, attempts, external_id FROM outbox_messages WHERE delivery_key=?",
                (delivery_key,),
            ).fetchone()
            if existing:
                if existing[1] in {"pending", "failed"}:
                    db.execute(
                        "UPDATE outbox_messages SET payload=?, status='pending', next_attempt_at=?, updated_at=? WHERE id=?",
                        (encoded, now, now, existing[0]),
                    )
                db.execute("COMMIT")
                return {"id": existing[0], "status": existing[1], "attempts": existing[2], "external_id": existing[3]}
            message_id = "out_" + uuid.uuid4().hex
            db.execute(
                "INSERT INTO outbox_messages VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, NULL, NULL, ?, ?)",
                (message_id, delivery_key, session_id, epoch, channel, target, encoded, now, now, now),
            )
            db.execute("COMMIT")
        return {"id": message_id, "status": "pending", "attempts": 0, "external_id": None}

    def claim_due(self, channel: str, limit: int = 20) -> list[dict[str, Any]]:
        """Lease due work atomically so two adapter processes cannot send it twice."""
        now = time.time()
        claimed: list[dict[str, Any]] = []
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT id, delivery_key, session_id, epoch, target, payload, attempts, external_id "
                "FROM outbox_messages WHERE channel=? AND status IN ('pending','failed') AND next_attempt_at<=? "
                "ORDER BY created_at ASC LIMIT ?",
                (channel, now, max(1, min(limit, 100))),
            ).fetchall()
            for row in rows:
                db.execute(
                    "UPDATE outbox_messages SET status='processing', attempts=attempts+1, updated_at=? WHERE id=?",
                    (now, row[0]),
                )
                claimed.append({
                    "id": row[0], "delivery_key": row[1], "session_id": row[2], "epoch": row[3],
                    "target": row[4], "payload": json.loads(row[5]), "attempts": row[6] + 1,
                    "external_id": row[7],
                })
            db.execute("COMMIT")
        return claimed

    def mark_sent(self, message_id: str, external_id: str | None = None) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE outbox_messages SET status='sent', external_id=COALESCE(?, external_id), last_error=NULL, updated_at=? WHERE id=?",
                (external_id, time.time(), message_id),
            )

    def retry(self, message_id: str, error: str, attempts: int) -> None:
        delay = min(300.0, 2.0 ** min(max(attempts - 1, 0), 8))
        now = time.time()
        with self._db() as db:
            db.execute(
                "UPDATE outbox_messages SET status='failed', last_error=?, next_attempt_at=?, updated_at=? WHERE id=?",
                (error[:1000], now + delay, now, message_id),
            )

    def cancel_session_before_epoch(self, session_id: str, epoch: int) -> int:
        """Prevent stale replies from leaving the Agent after a newer turn."""
        with self._db() as db:
            cursor = db.execute(
                "UPDATE outbox_messages SET status='cancelled', updated_at=? "
                "WHERE session_id=? AND epoch<? AND status IN ('pending','failed','processing')",
                (time.time(), session_id, epoch),
            )
        return int(cursor.rowcount)

    def recover_processing(self) -> int:
        """A process crash releases unfinished delivery leases on the next boot."""
        with self._db() as db:
            cursor = db.execute(
                "UPDATE outbox_messages SET status='failed', next_attempt_at=?, updated_at=? WHERE status='processing'",
                (time.time(), time.time()),
            )
        return int(cursor.rowcount)
