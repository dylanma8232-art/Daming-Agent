"""会话隔离的子 Agent 与持久化 Cron 运行时。"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable

from runtime_store import RuntimeStore


def _field_matches(value: str, actual: int) -> bool:
    for part in value.split(","):
        if part == "*": return True
        if part.startswith("*/") and part[2:].isdigit() and actual % int(part[2:]) == 0: return True
        if part.isdigit() and int(part) == actual: return True
    return False


def validate_schedule(expression: str) -> None:
    if expression.startswith("every:"):
        if float(expression.split(":", 1)[1]) <= 0: raise ValueError("every 间隔必须大于 0")
        return
    fields = expression.split()
    if len(fields) != 5: raise ValueError("Cron 使用 5 段表达式，例如 '0 9 * * *'，或 every:<秒>")
    for field in fields[:2]:
        if not all(token == "*" or token.isdigit() or (token.startswith("*/") and token[2:].isdigit()) for token in field.split(",")):
            raise ValueError("当前 Cron 仅支持 *, 数字, 逗号和 */N")


def is_due(expression: str, last_run: float, now: float) -> bool:
    if expression.startswith("every:"):
        return now - last_run >= float(expression.split(":", 1)[1])
    current = datetime.fromtimestamp(now)
    if last_run and int(last_run // 60) == int(now // 60): return False
    minute, hour, day, month, weekday = expression.split()
    return (_field_matches(minute, current.minute) and _field_matches(hour, current.hour)
            and _field_matches(day, current.day) and _field_matches(month, current.month)
            and _field_matches(weekday, (current.weekday() + 1) % 7))


class SubagentManager:
    """真正并发的子任务工作器；上下文与 workspace 均由独立 session_id 隔离。"""
    def __init__(self, store: RuntimeStore, execute: Callable[[str, str], str], max_workers: int = 4, on_terminal: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.store, self.execute = store, execute
        self.on_terminal = on_terminal
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="daming-subagent")
        self.cancelled: set[str] = set()
        self.lock = threading.RLock()
        self._recover()

    def _recover(self) -> None:
        for row in self.store.subagents(limit=500):
            if row.get("status") in {"queued", "running"}:
                self.store.subagent(row["id"], status="interrupted", error="重启后不会自动重放子 Agent", recovery_note="可由主 Agent 重新创建")

    def spawn(self, session_id: str, objective: str, role: str = "executor", parent_run_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not objective.strip(): raise ValueError("子 Agent 目标不能为空")
        agent_id = "sub_" + uuid.uuid4().hex[:12]
        child_session = f"{session_id}::subagent::{agent_id}"
        record = self.store.subagent(agent_id, session_id=session_id, child_session_id=child_session, parent_run_id=parent_run_id, role=role, objective=objective, status="queued", progress="等待执行", **(metadata or {}))
        self.store.audit(session_id=session_id, event_type="subagent_created", subagent_id=agent_id, role=role)
        self.pool.submit(self._run, agent_id)
        return record

    def spawn_many(self, session_id: str, workers: list[dict[str, Any]], parent_run_id: str | None = None) -> list[dict[str, Any]]:
        return [self.spawn(session_id, str(item.get("objective", "")), str(item.get("role", "executor")), parent_run_id) for item in workers]

    def _run(self, agent_id: str) -> None:
        record = self.store.get_subagent(agent_id)
        if not record or agent_id in self.cancelled: return
        self.store.subagent(agent_id, status="running", progress="正在推理与执行")
        try:
            answer = self.execute(record["objective"], record["child_session_id"])
            if agent_id in self.cancelled:
                self.store.subagent(agent_id, status="cancelled", progress="已取消", result_preview=answer[:1000])
            else:
                self.store.subagent(agent_id, status="completed", progress="已完成", result_preview=answer[:4000])
            self.store.audit(session_id=record["session_id"], event_type="subagent_finished", subagent_id=agent_id, status=self.store.get_subagent(agent_id).get("status"))
        except Exception as error:
            self.store.subagent(agent_id, status="failed", progress="执行失败", error=str(error))
            self.store.audit(session_id=record["session_id"], event_type="subagent_failed", subagent_id=agent_id)
        finally:
            if self.on_terminal:
                final_record = self.store.get_subagent(agent_id)
                if final_record:
                    try:
                        self.on_terminal(final_record)
                    except Exception as error:
                        self.store.audit(session_id=record.get("session_id"), event_type="subagent_terminal_callback_failed", subagent_id=agent_id, error=str(error))

    def cancel(self, agent_id: str, session_id: str) -> bool:
        record = self.store.get_subagent(agent_id, session_id)
        if not record or record.get("status") in {"completed", "failed", "cancelled", "interrupted"}: return False
        with self.lock: self.cancelled.add(agent_id)
        self.store.subagent(agent_id, status="cancelled", progress="已请求取消")
        self.store.audit(session_id=session_id, event_type="subagent_cancelled", subagent_id=agent_id)
        return True


class CronManager:
    """重启可恢复的 Cron；执行由 Agent 回调完成，所以审批/审计保持一致。"""
    def __init__(self, store: RuntimeStore, execute: Callable[[str, str], str], poll_seconds: float = 5) -> None:
        self.store, self.execute, self.poll_seconds = store, execute, poll_seconds
        self.stop_event = threading.Event(); self.lock = threading.RLock()
        self._recover(); self.worker = threading.Thread(target=self._loop, daemon=True, name="daming-cron"); self.worker.start()

    def _recover(self) -> None:
        for row in self.store.cron_jobs(limit=500):
            if row.get("status") == "running": self.store.cron_job(row["id"], status="active", last_error="重启时中断；等待下一次触发")

    def create(self, session_id: str, name: str, expression: str, prompt: str) -> dict[str, Any]:
        if not name.strip() or not prompt.strip(): raise ValueError("名称和任务内容不能为空")
        validate_schedule(expression)
        job_id = "cron_" + uuid.uuid4().hex[:12]
        row = self.store.cron_job(job_id, session_id=session_id, name=name[:100], expression=expression, prompt=prompt, status="active", last_run_at=0, run_count=0)
        self.store.audit(session_id=session_id, event_type="cron_created", cron_id=job_id, expression=expression)
        return row

    def set_status(self, job_id: str, session_id: str, active: bool) -> bool:
        row = self.store.get_cron_job(job_id, session_id)
        if not row: return False
        self.store.cron_job(job_id, status="active" if active else "paused")
        self.store.audit(session_id=session_id, event_type="cron_resumed" if active else "cron_paused", cron_id=job_id)
        return True

    def delete(self, job_id: str, session_id: str) -> bool:
        row = self.store.get_cron_job(job_id, session_id)
        if not row: return False
        self.store.cron_job(job_id, status="deleted", deleted_at=time.time())
        self.store.audit(session_id=session_id, event_type="cron_deleted", cron_id=job_id)
        return True

    def tick(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now; triggered = []
        for row in self.store.cron_jobs(limit=500):
            if row.get("status") != "active" or not is_due(row.get("expression", ""), float(row.get("last_run_at", 0)), now): continue
            self.store.cron_job(row["id"], status="running", last_run_at=now)
            threading.Thread(target=self._execute, args=(row["id"],), daemon=True, name=f"cron-{row['id']}").start(); triggered.append(row["id"])
        return triggered

    def _execute(self, job_id: str) -> None:
        row = self.store.get_cron_job(job_id)
        if not row: return
        try:
            answer = self.execute(row["prompt"], f"{row['session_id']}::cron::{job_id}")
            current = self.store.get_cron_job(job_id) or row
            self.store.cron_job(job_id, status="active" if current.get("status") != "deleted" else "deleted", run_count=int(row.get("run_count", 0)) + 1, last_result_preview=answer[:1500], last_error=None, last_completed_at=time.time())
            self.store.audit(session_id=row["session_id"], event_type="cron_finished", cron_id=job_id)
        except Exception as error:
            self.store.cron_job(job_id, status="active", last_error=str(error), last_completed_at=time.time())
            self.store.audit(session_id=row["session_id"], event_type="cron_failed", cron_id=job_id)

    def _loop(self) -> None:
        while not self.stop_event.wait(self.poll_seconds): self.tick()

    def stop(self) -> None: self.stop_event.set()
