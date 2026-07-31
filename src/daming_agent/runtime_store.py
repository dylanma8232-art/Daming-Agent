"""持久化运行记录；所有对外读取均已脱敏。"""
import json
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {"api_key", "apikey", "token", "access_token", "refresh_token", "secret", "password", "authorization", "cookie", "credentials"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "***" if key.lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class RuntimeStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = root / "runtime.json"
        self.lock = threading.RLock()
        self.data = self._read()

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {"tasks": data.get("tasks", {}), "subagents": data.get("subagents", {}), "cron_jobs": data.get("cron_jobs", {}), "approvals": data.get("approvals", {}), "runs": data.get("runs", {}), "task_graphs": data.get("task_graphs", {}), "task_nodes": data.get("task_nodes", {}), "audit": data.get("audit", [])}
        except Exception:
            return {"tasks": {}, "subagents": {}, "cron_jobs": {}, "approvals": {}, "runs": {}, "task_graphs": {}, "task_nodes": {}, "audit": []}

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def task(self, task_id: str, **fields: Any) -> dict[str, Any]:
        with self.lock:
            record = self.data["tasks"].setdefault(task_id, {"id": task_id, "created_at": time.time()})
            record.update(redact(fields)); record["updated_at"] = time.time(); self._save()
            return deepcopy(record)

    def get_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        with self.lock:
            record = self.data["tasks"].get(task_id)
            if not record or (session_id and record.get("session_id") != session_id): return None
            return deepcopy(record)

    def tasks(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = [row for row in self.data["tasks"].values() if not session_id or row.get("session_id") == session_id]
            return deepcopy(sorted(rows, key=lambda row: row.get("updated_at", 0), reverse=True)[:max(1, min(limit, 500))])

    def subagent(self, agent_id: str, **fields: Any) -> dict[str, Any]:
        return self._record("subagents", agent_id, **fields)

    def get_subagent(self, agent_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        return self._get("subagents", agent_id, session_id)

    def subagents(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self._rows("subagents", session_id, limit)

    def cron_job(self, job_id: str, **fields: Any) -> dict[str, Any]:
        return self._record("cron_jobs", job_id, **fields)

    def get_cron_job(self, job_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        return self._get("cron_jobs", job_id, session_id)

    def cron_jobs(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self._rows("cron_jobs", session_id, limit)

    # Task Graph is the durable coordination layer for complex user tasks.  It
    # deliberately lives beside existing runs/subagents so old sessions remain
    # fully compatible and a graph can reference their records by ID.
    def task_graph(self, graph_id: str, **fields: Any) -> dict[str, Any]:
        return self._record("task_graphs", graph_id, **fields)

    def get_task_graph(self, graph_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        return self._get("task_graphs", graph_id, session_id)

    def task_graphs(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self._rows("task_graphs", session_id, limit)

    def task_node(self, node_id: str, **fields: Any) -> dict[str, Any]:
        return self._record("task_nodes", node_id, **fields)

    def get_task_node(self, node_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        return self._get("task_nodes", node_id, session_id)

    def task_nodes(self, graph_id: str | None = None, session_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        rows = self._rows("task_nodes", session_id, limit)
        return [row for row in rows if not graph_id or row.get("graph_id") == graph_id]

    def _record(self, collection: str, record_id: str, **fields: Any) -> dict[str, Any]:
        with self.lock:
            records = self.data.setdefault(collection, {})
            record = records.setdefault(record_id, {"id": record_id, "created_at": time.time()})
            record.update(redact(fields)); record["updated_at"] = time.time(); self._save()
            return deepcopy(record)

    def _get(self, collection: str, record_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        with self.lock:
            record = self.data.get(collection, {}).get(record_id)
            if not record or (session_id and record.get("session_id") != session_id): return None
            return deepcopy(record)

    def _rows(self, collection: str, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = [row for row in self.data.get(collection, {}).values() if not session_id or row.get("session_id") == session_id]
            return deepcopy(sorted(rows, key=lambda row: row.get("updated_at", 0), reverse=True)[:max(1, min(limit, 500))])

    def run(self, run_id: str, **fields: Any) -> dict[str, Any]:
        with self.lock:
            record = self.data["runs"].setdefault(run_id, {"id": run_id, "created_at": time.time(), "steps": []})
            record.update(redact(fields)); record["updated_at"] = time.time(); self._save()
            return deepcopy(record)

    def finish_run(self, run_id: str, status: str, **fields: Any) -> bool:
        """Atomically finish an active run without resurrecting terminal state.

        Recovery and a late worker can race during host restarts.  A terminal
        record (especially one that already has an answer preview) is the
        source of truth and must never be overwritten back to ``interrupted``.
        """
        terminal = {"completed", "failed", "cancelled", "interrupted"}
        if status not in terminal:
            raise ValueError(f"run status must be terminal, got {status!r}")
        with self.lock:
            record = self.data["runs"].get(run_id)
            if record is None or record.get("status") in terminal:
                return False
            record.update(redact(fields))
            record["status"] = status
            record["updated_at"] = time.time()
            self._save()
            return True

    def interrupt_unfinished_runs(self, note: str) -> list[dict[str, Any]]:
        """Mark only genuinely unfinished runs interrupted during startup.

        If an earlier worker persisted an answer before dying, preserve it as a
        completed run.  This makes recovery safe even when an old process and a
        newly-started process briefly overlap.
        """
        recovered: list[dict[str, Any]] = []
        active = {"running", "running_recovered"}
        with self.lock:
            changed = False
            for record in self.data["runs"].values():
                if record.get("status") not in active:
                    continue
                if record.get("answer_preview"):
                    record.update({"status": "completed", "current_step": "回复已持久化", "recovery_note": "启动恢复时发现已持久化回复", "updated_at": time.time()})
                else:
                    record.update({"status": "interrupted", "current_step": "已中断", "recovery_note": note, "updated_at": time.time()})
                recovered.append(deepcopy(record))
                changed = True
            if changed:
                self._save()
        return recovered

    def add_run_step(self, run_id: str, **step: Any) -> None:
        with self.lock:
            record = self.data["runs"].setdefault(run_id, {"id": run_id, "created_at": time.time(), "steps": []})
            record.setdefault("steps", []).append({"at": time.time(), **redact(step)})
            record["updated_at"] = time.time(); self._save()

    def audit(self, **event: Any) -> None:
        with self.lock:
            self.data["audit"].append({"at": time.time(), **redact(event)})
            self.data["audit"] = self.data["audit"][-2000:]; self._save()

    def request_approval(self, approval_id: str, **fields: Any) -> dict[str, Any]:
        with self.lock:
            record = {"id": approval_id, "status": "pending", "created_at": time.time(), **redact(fields)}
            self.data["approvals"][approval_id] = record; self._save(); return deepcopy(record)

    def claim_approval(self, approval_id: str, approved: bool) -> dict[str, Any] | None:
        """原子地领取一次审批，防止双击或并发请求重复执行。"""
        with self.lock:
            record = self.data["approvals"].get(approval_id)
            if not record or record.get("status") != "pending": return None
            record.update({"status": "executing" if approved else "rejected", "resolved_at": time.time()})
            self._save(); return deepcopy(record)

    def finish_approval(self, approval_id: str, status: str, **fields: Any) -> bool:
        with self.lock:
            record = self.data["approvals"].get(approval_id)
            if not record or record.get("status") != "executing": return False
            record.update({"status": status, "completed_at": time.time(), **redact(fields)}); self._save(); return True

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        return self.claim_approval(approval_id, approved) is not None

    def approvals(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = [row for row in self.data["approvals"].values() if not session_id or row.get("session_id") == session_id]
            return deepcopy(sorted(rows, key=lambda row: row.get("created_at", 0), reverse=True)[:max(1, min(limit, 500))])

    def audit_rows(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = [row for row in self.data["audit"] if not session_id or row.get("session_id") == session_id]
            return deepcopy(list(reversed(rows[-max(1, min(limit, 500)):])) )

    def summary(self, session_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        return {"tasks": self.tasks(session_id, limit), "task_graphs": self.task_graphs(session_id, limit), "approvals": self.approvals(session_id, limit), "audit": self.audit_rows(session_id, limit)}
