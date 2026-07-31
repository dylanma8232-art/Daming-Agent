"""Durable, dependency-aware coordination for complex Agent tasks.

This is intentionally a small runtime primitive, not an LLM planner.  The LLM
may propose nodes, but this module validates their dependency graph and only
dispatches nodes whose prerequisites are complete.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from runtime_store import RuntimeStore


TERMINAL = {"completed", "failed", "cancelled", "interrupted", "compensated"}
VERIFICATION_KINDS = {"subagent_success", "result_contains"}


class TaskGraphManager:
    """Persist task nodes, unlock dependencies, and connect subagent outcomes."""

    def __init__(self, store: RuntimeStore) -> None:
        self.store = store
        self.lock = threading.RLock()
        self._recover()

    def _recover(self) -> None:
        """Never replay a side-effecting node after a restart without a new dispatch."""
        for node in self.store.task_nodes(limit=500):
            if node.get("status") in {"dispatching", "running"}:
                self.store.task_node(node["id"], status="interrupted", recovery_note="重启后未自动重放；可显式重试该节点")
        for graph in self.store.task_graphs(limit=500):
            if graph.get("status") == "running":
                self.store.task_graph(graph["id"], status="paused", recovery_note="重启后等待显式继续调度")

    def create(self, session_id: str, title: str, nodes: list[dict[str, Any]], root_run_id: str | None = None, max_nodes: int = 32) -> dict[str, Any]:
        if not title.strip() or not nodes:
            raise ValueError("任务图必须包含标题和至少一个节点")
        if len(nodes) > max_nodes:
            raise ValueError(f"单个任务图最多允许 {max_nodes} 个节点")
        local_ids = [str(node.get("id", "")).strip() for node in nodes]
        if any(not node_id for node_id in local_ids) or len(set(local_ids)) != len(local_ids):
            raise ValueError("每个节点都需要唯一 id")
        known = set(local_ids)
        dependencies = {node_id: [str(dep) for dep in dict(nodes[index]).get("depends_on", [])] for index, node_id in enumerate(local_ids)}
        if any(set(deps) - known for deps in dependencies.values()):
            raise ValueError("任务节点依赖了不存在的节点")
        self._validate_acyclic(dependencies)

        graph_id = "graph_" + uuid.uuid4().hex[:12]
        self.store.task_graph(graph_id, session_id=session_id, title=title[:200], root_run_id=root_run_id, status="active", node_count=len(nodes))
        for raw, local_id in zip(nodes, local_ids):
            deps = dependencies[local_id]
            node_id = f"{graph_id}:{local_id}"
            self.store.task_node(
                node_id,
                session_id=session_id,
                graph_id=graph_id,
                local_id=local_id,
                objective=str(raw.get("objective", "")).strip(),
                role=str(raw.get("role", "executor")).strip() or "executor",
                depends_on=deps,
                verification=self._normalize_verification(raw.get("verification")),
                compensation_objective=str(raw.get("compensation_objective", "")).strip(),
                compensation_role=str(raw.get("compensation_role", "executor")).strip() or "executor",
                status="ready" if not deps else "waiting",
                attempts=0,
            )
        self.store.audit(session_id=session_id, event_type="task_graph_created", graph_id=graph_id, node_count=len(nodes))
        return self.snapshot(graph_id, session_id)

    def add_node(self, graph_id: str, session_id: str, node: dict[str, Any], max_nodes: int = 32) -> dict[str, Any]:
        """Apply the only supported dynamic plan patch: append a new safe node.

        Existing nodes, especially completed ones, are immutable. This makes a
        model's re-plan auditable and prevents it from silently rewriting work.
        """
        with self.lock:
            graph = self.store.get_task_graph(graph_id, session_id)
            if not graph or graph.get("status") in TERMINAL | {"rolled_back", "rolling_back"}:
                raise ValueError("任务图不存在或不允许再修改")
            current = self.store.task_nodes(graph_id, session_id)
            if len(current) >= max_nodes:
                raise ValueError(f"单个任务图最多允许 {max_nodes} 个节点")
            local_id = str(node.get("id", "")).strip()
            if not local_id or any(row.get("local_id") == local_id for row in current):
                raise ValueError("新节点需要未使用过的 id")
            deps = [str(dep) for dep in node.get("depends_on", [])]
            known = {row.get("local_id") for row in current}
            if set(deps) - known:
                raise ValueError("新节点依赖了不存在的节点")
            node_id = f"{graph_id}:{local_id}"
            self.store.task_node(
                node_id,
                session_id=session_id,
                graph_id=graph_id,
                local_id=local_id,
                objective=str(node.get("objective", "")).strip(),
                role=str(node.get("role", "executor")).strip() or "executor",
                depends_on=deps,
                verification=self._normalize_verification(node.get("verification")),
                compensation_objective=str(node.get("compensation_objective", "")).strip(),
                compensation_role=str(node.get("compensation_role", "executor")).strip() or "executor",
                status="ready" if not deps else "waiting",
                attempts=0,
                added_dynamically=True,
            )
            self.store.task_graph(graph_id, node_count=len(current) + 1)
            self.store.audit(session_id=session_id, event_type="task_graph_node_added", graph_id=graph_id, node_id=local_id)
            self._unlock_ready_nodes(graph_id, session_id)
            return self.snapshot(graph_id, session_id)

    def snapshot(self, graph_id: str, session_id: str | None = None) -> dict[str, Any]:
        graph = self.store.get_task_graph(graph_id, session_id)
        if not graph:
            raise ValueError("任务图不存在")
        nodes = sorted(self.store.task_nodes(graph_id, session_id), key=lambda node: node.get("created_at", 0))
        return {**graph, "nodes": nodes}

    def dispatch(self, graph_id: str, session_id: str, spawn: Callable[[dict[str, Any]], str]) -> list[str]:
        """Dispatch every currently-ready node.  The callback returns a subagent ID."""
        with self.lock:
            graph = self.store.get_task_graph(graph_id, session_id)
            if not graph:
                raise ValueError("任务图不存在")
            if graph.get("status") in TERMINAL | {"paused", "rolling_back", "rolled_back"}:
                return []
            self._unlock_ready_nodes(graph_id, session_id)
            ready = [node for node in self.store.task_nodes(graph_id, session_id) if node.get("status") == "ready"]
            dispatched: list[str] = []
            for node in ready:
                self.store.task_node(node["id"], status="dispatching", attempts=int(node.get("attempts", 0)) + 1)
                try:
                    subagent_id = spawn(node)
                    # A very fast worker can finish before spawn() returns. Do
                    # not overwrite that terminal outcome with "running".
                    current = self.store.get_task_node(node["id"], session_id)
                    if current and current.get("status") == "dispatching":
                        self.store.task_node(node["id"], status="running", subagent_id=subagent_id, started_at=time.time())
                    dispatched.append(node["local_id"])
                except Exception as error:
                    self.store.task_node(node["id"], status="failed", error=str(error)[:500])
            self._refresh_graph(graph_id, session_id)
            return dispatched

    def complete_from_subagent(self, record: dict[str, Any]) -> None:
        node_id = record.get("task_node_id")
        graph_id = record.get("task_graph_id")
        if not node_id or not graph_id:
            return
        node = self.store.get_task_node(str(node_id), record.get("session_id"))
        if not node or node.get("status") in TERMINAL:
            return
        result_preview = str(record.get("result_preview", ""))[:4000]
        status = "completed" if record.get("status") == "completed" else record.get("status", "failed")
        if status not in TERMINAL:
            status = "failed"
        verification = self._verify(node, result_preview) if status == "completed" else {"passed": False, "detail": str(record.get("error", "子 Agent 未成功完成"))[:500]}
        if not verification["passed"]:
            status = "failed"
        self.store.task_node(node["id"], status=status, result_preview=result_preview, error=record.get("error") or (None if verification["passed"] else verification["detail"]), verification_outcome=verification, completed_at=time.time())
        if node.get("is_compensation") and status == "completed":
            self.store.task_node(node["original_node_id"], status="compensated", compensated_at=time.time())
        self._unlock_ready_nodes(str(graph_id), str(record.get("session_id", "")))
        self._refresh_graph(str(graph_id), str(record.get("session_id", "")))

    def wait_for_approval(self, graph_id: str, node_id: str, session_id: str, approval_ids: list[str], previous_result: str) -> None:
        node = self.store.get_task_node(node_id, session_id)
        if not node:
            return
        self.store.task_node(node_id, status="waiting_approval", approval_ids=approval_ids, previous_result_preview=previous_result[:4000])
        self.store.task_graph(graph_id, status="waiting_approval")

    def resolve_approval(self, approval_id: str, approved: bool, session_id: str) -> str | None:
        """Return the graph ID that became dispatchable after an approval decision."""
        for node in self.store.task_nodes(session_id=session_id):
            if approval_id not in node.get("approval_ids", []):
                continue
            if not approved:
                self.store.task_node(node["id"], status="failed", error="审批被拒绝")
                self._unlock_ready_nodes(node["graph_id"], session_id)
                self._refresh_graph(node["graph_id"], session_id)
                return node["graph_id"]
            remaining = [item for item in node.get("approval_ids", []) if item != approval_id]
            self.store.task_node(node["id"], approval_ids=remaining)
            if not remaining:
                self.store.task_node(node["id"], status="ready", approval_context="此前高风险操作已获批准并执行；继续完成任务，不要重复该操作。")
                self.store.task_graph(node["graph_id"], status="active")
            return node["graph_id"]
        return None

    def rollback(self, graph_id: str, session_id: str) -> list[str]:
        """Create reverse-dependency compensation nodes; they still go through normal approval policy."""
        graph = self.store.get_task_graph(graph_id, session_id)
        if not graph:
            raise ValueError("任务图不存在")
        originals = [node for node in self.store.task_nodes(graph_id, session_id) if node.get("status") == "completed" and node.get("compensation_objective") and not node.get("is_compensation")]
        by_local_id = {node["local_id"]: node for node in originals}
        created: list[str] = []
        for original in originals:
            local_id = f"rollback__{original['local_id']}"
            if self._node_by_local_id(graph_id, local_id, session_id):
                continue
            # Reverse each direct dependency: compensate a dependent before the
            # node it relied on.
            deps = [f"rollback__{candidate['local_id']}" for candidate in originals if original["local_id"] in candidate.get("depends_on", [])]
            node_id = f"{graph_id}:{local_id}"
            self.store.task_node(node_id, session_id=session_id, graph_id=graph_id, local_id=local_id, objective=original["compensation_objective"], role=original.get("compensation_role", "executor"), depends_on=deps, verification={"kind": "subagent_success", "description": "补偿动作成功完成"}, status="ready" if not deps else "waiting", attempts=0, is_compensation=True, original_node_id=original["id"])
            self.store.task_node(original["id"], status="compensating")
            created.append(local_id)
        self.store.task_graph(graph_id, status="active" if created else "rolled_back", rollback_requested_at=time.time())
        self._unlock_ready_nodes(graph_id, session_id)
        return created

    def retry_node(self, graph_id: str, local_id: str, session_id: str) -> bool:
        node = self._node_by_local_id(graph_id, local_id, session_id)
        if not node or node.get("status") not in {"failed", "interrupted", "cancelled"}:
            return False
        self.store.task_node(node["id"], status="ready", error=None, recovery_note=None)
        self.store.task_graph(graph_id, status="active")
        return True

    def _node_by_local_id(self, graph_id: str, local_id: str, session_id: str) -> dict[str, Any] | None:
        for node in self.store.task_nodes(graph_id, session_id):
            if node.get("local_id") == local_id:
                return node
        return None

    def _unlock_ready_nodes(self, graph_id: str, session_id: str) -> None:
        nodes = self.store.task_nodes(graph_id, session_id)
        by_local_id = {node.get("local_id"): node for node in nodes}
        for node in nodes:
            if node.get("status") not in {"waiting", "blocked"}:
                continue
            dependency_states = [by_local_id[dep].get("status") for dep in node.get("depends_on", [])]
            if all(state == "completed" for state in dependency_states):
                self.store.task_node(node["id"], status="ready")
            elif any(state in {"failed", "cancelled", "interrupted"} for state in dependency_states):
                self.store.task_node(node["id"], status="blocked", error="前置任务未成功完成")

    def _refresh_graph(self, graph_id: str, session_id: str) -> None:
        nodes = self.store.task_nodes(graph_id, session_id)
        statuses = {node.get("status") for node in nodes}
        original_nodes = [node for node in nodes if not node.get("is_compensation")]
        compensation_nodes = [node for node in nodes if node.get("is_compensation")]
        if compensation_nodes and all(node.get("status") == "completed" for node in compensation_nodes):
            status = "rolled_back"
        elif nodes and statuses == {"completed"}:
            status = "completed"
        elif statuses & {"waiting_approval"}:
            status = "waiting_approval"
        elif statuses & {"failed", "blocked", "cancelled", "interrupted"}:
            status = "needs_attention"
        elif statuses & {"running", "dispatching"}:
            status = "running"
        else:
            status = "active"
        self.store.task_graph(graph_id, status=status, completed_nodes=sum(node.get("status") == "completed" for node in original_nodes))

    @staticmethod
    def _normalize_verification(raw: Any) -> dict[str, str]:
        if isinstance(raw, str):
            return {"kind": "subagent_success", "description": raw[:500] or "子 Agent 成功完成并返回结果"}
        if not isinstance(raw, dict):
            return {"kind": "subagent_success", "description": "子 Agent 成功完成并返回结果"}
        kind = str(raw.get("kind", "subagent_success"))
        if kind not in VERIFICATION_KINDS:
            raise ValueError("不支持的验收类型")
        expected = str(raw.get("expected", ""))
        if kind == "result_contains" and not expected:
            raise ValueError("result_contains 验收需要 expected")
        return {"kind": kind, "expected": expected[:500], "description": str(raw.get("description", ""))[:500]}

    @staticmethod
    def _verify(node: dict[str, Any], result: str) -> dict[str, Any]:
        policy = node.get("verification") or {"kind": "subagent_success"}
        if policy.get("kind") == "result_contains":
            expected = policy.get("expected", "")
            return {"passed": expected.lower() in result.lower(), "kind": "result_contains", "detail": f"结果必须包含: {expected}"}
        return {"passed": True, "kind": "subagent_success", "detail": policy.get("description") or "子 Agent 成功完成"}

    @staticmethod
    def _validate_acyclic(dependencies: dict[str, list[str]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("任务图存在循环依赖")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in dependencies[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in dependencies:
            visit(node_id)

    def create_supervisor_governance_graph(self, session_id: str, title: str, supervisor_objective: str, worker_tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """按 Hierarchical Supervisor（分层主从治理）范式自动构建拓扑任务图：

        包含：
        1. Supervisor 主控节点 (supervisor_plan): 主控 Agent 进行初始化规划与资源分发；
        2. Worker 子任务节点 (worker_1, worker_2...): 由隔离上下文的 Worker 跑具体执行；
        3. Auditor 独立审计节点 (auditor_review): 由 Reviewer/Auditor 进行独立验收与防错检查。
        """
        nodes: list[dict[str, Any]] = [
            {
                "id": "supervisor_plan",
                "objective": f"【Supervisor 主控规划】{supervisor_objective}",
                "role": "supervisor",
                "depends_on": [],
            }
        ]

        worker_ids = []
        for idx, task in enumerate(worker_tasks, start=1):
            w_id = str(task.get("id", f"worker_{idx}")).strip()
            worker_ids.append(w_id)
            deps = [str(d) for d in task.get("depends_on", [])] or ["supervisor_plan"]
            nodes.append({
                "id": w_id,
                "objective": str(task.get("objective", f"Worker 任务 {idx}")).strip(),
                "role": str(task.get("role", "executor")).strip() or "executor",
                "depends_on": deps,
                "verification": task.get("verification"),
            })

        nodes.append({
            "id": "auditor_review",
            "objective": f"【Auditor 独立质量与安全审计】复核所有 Worker ({', '.join(worker_ids)}) 的交付物与代码改动，确保符合规范",
            "role": "reviewer",
            "depends_on": worker_ids,
            "verification": {"kind": "subagent_success", "description": "独立审计通过"},
        })

        return self.create(session_id=session_id, title=f"【Supervisor 分层治理】{title}", nodes=nodes)

