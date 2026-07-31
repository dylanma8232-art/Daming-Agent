import tempfile
import time
import unittest
from pathlib import Path

from orchestration import SubagentManager
from runtime_store import RuntimeStore
from task_graph import TaskGraphManager


class TaskGraphTests(unittest.TestCase):
    def setUp(self):
        self.store = RuntimeStore(Path(tempfile.mkdtemp()) / "runtime")
        self.graphs = TaskGraphManager(self.store)

    def test_dependency_fan_out_and_fan_in(self):
        graph = self.graphs.create(
            "session-a",
            "research then deliver",
            [
                {"id": "research-a", "objective": "research A", "role": "researcher"},
                {"id": "research-b", "objective": "research B", "role": "researcher"},
                {"id": "synthesis", "objective": "synthesize", "depends_on": ["research-a", "research-b"], "role": "reviewer"},
            ],
        )
        graph_id = graph["id"]
        spawned = []
        self.assertEqual(set(self.graphs.dispatch(graph_id, "session-a", lambda node: spawned.append(node["local_id"]) or f"sub-{node['local_id']}")), {"research-a", "research-b"})
        self.assertEqual(set(spawned), {"research-a", "research-b"})

        for local_id in ("research-a", "research-b"):
            node = next(item for item in self.graphs.snapshot(graph_id, "session-a")["nodes"] if item["local_id"] == local_id)
            self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": node["id"], "status": "completed", "result_preview": "ok"})

        self.assertEqual(self.graphs.dispatch(graph_id, "session-a", lambda node: spawned.append(node["local_id"]) or "sub-synthesis"), ["synthesis"])
        synthesis = next(item for item in self.graphs.snapshot(graph_id, "session-a")["nodes"] if item["local_id"] == "synthesis")
        self.assertEqual(synthesis["status"], "running")

    def test_failed_dependency_blocks_descendant_and_retry_is_local(self):
        graph = self.graphs.create("session-a", "repair", [
            {"id": "build", "objective": "build"},
            {"id": "verify", "objective": "verify", "depends_on": ["build"]},
        ])
        graph_id = graph["id"]
        self.graphs.dispatch(graph_id, "session-a", lambda node: "sub-build")
        build = next(item for item in self.graphs.snapshot(graph_id, "session-a")["nodes"] if item["local_id"] == "build")
        self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": build["id"], "status": "failed", "error": "compile error"})
        state = self.graphs.snapshot(graph_id, "session-a")
        verify = next(item for item in state["nodes"] if item["local_id"] == "verify")
        self.assertEqual(verify["status"], "blocked")
        self.assertEqual(state["status"], "needs_attention")
        self.assertTrue(self.graphs.retry_node(graph_id, "build", "session-a"))
        self.assertFalse(self.graphs.retry_node(graph_id, "verify", "session-a"))

    def test_rejects_cycles_and_unknown_dependencies(self):
        with self.assertRaises(ValueError):
            self.graphs.create("session-a", "cycle", [
                {"id": "a", "objective": "a", "depends_on": ["b"]},
                {"id": "b", "objective": "b", "depends_on": ["a"]},
            ])
        with self.assertRaises(ValueError):
            self.graphs.create("session-a", "unknown", [{"id": "a", "objective": "a", "depends_on": ["missing"]}])

    def test_subagent_terminal_callback_advances_graph(self):
        graph = self.graphs.create("session-a", "one node", [{"id": "work", "objective": "do work"}])
        graph_id = graph["id"]
        manager = SubagentManager(self.store, lambda objective, session: "done", on_terminal=self.graphs.complete_from_subagent)
        try:
            self.graphs.dispatch(
                graph_id,
                "session-a",
                lambda node: manager.spawn("session-a", node["objective"], metadata={"task_graph_id": graph_id, "task_node_id": node["id"]})["id"],
            )
            for _ in range(50):
                if self.graphs.snapshot(graph_id, "session-a")["status"] == "completed":
                    break
                time.sleep(.02)
            self.assertEqual(self.graphs.snapshot(graph_id, "session-a")["status"], "completed")
        finally:
            manager.pool.shutdown(wait=True)

    def test_dynamic_node_and_structured_acceptance(self):
        graph = self.graphs.create("session-a", "dynamic", [{"id": "a", "objective": "first"}])
        graph_id = graph["id"]
        self.graphs.add_node(graph_id, "session-a", {
            "id": "review", "objective": "return an approved report", "depends_on": ["a"],
            "verification": {"kind": "result_contains", "expected": "APPROVED"},
        })
        self.graphs.dispatch(graph_id, "session-a", lambda node: "sub-a")
        first = next(row for row in self.graphs.snapshot(graph_id, "session-a")["nodes"] if row["local_id"] == "a")
        self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": first["id"], "status": "completed", "result_preview": "done"})
        self.graphs.dispatch(graph_id, "session-a", lambda node: "sub-review")
        review = next(row for row in self.graphs.snapshot(graph_id, "session-a")["nodes"] if row["local_id"] == "review")
        self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": review["id"], "status": "completed", "result_preview": "report pending"})
        self.assertEqual(self.graphs.snapshot(graph_id, "session-a")["status"], "needs_attention")

    def test_approval_wait_and_reverse_compensation(self):
        graph = self.graphs.create("session-a", "rollback", [
            {"id": "create", "objective": "create", "compensation_objective": "delete create"},
            {"id": "publish", "objective": "publish", "depends_on": ["create"], "compensation_objective": "unpublish"},
        ])
        graph_id = graph["id"]
        for local_id in ("create", "publish"):
            node = next(row for row in self.graphs.snapshot(graph_id, "session-a")["nodes"] if row["local_id"] == local_id)
            self.store.task_node(node["id"], status="completed")
        created = self.graphs.rollback(graph_id, "session-a")
        self.assertEqual(set(created), {"rollback__create", "rollback__publish"})
        self.assertEqual(self.graphs.dispatch(graph_id, "session-a", lambda node: f"sub-{node['local_id']}"), ["rollback__publish"])
        publish_rollback = next(row for row in self.graphs.snapshot(graph_id, "session-a")["nodes"] if row["local_id"] == "rollback__publish")
        self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": publish_rollback["id"], "status": "completed", "result_preview": "done"})
        self.assertEqual(self.graphs.dispatch(graph_id, "session-a", lambda node: f"sub-{node['local_id']}"), ["rollback__create"])
        create_rollback = next(row for row in self.graphs.snapshot(graph_id, "session-a")["nodes"] if row["local_id"] == "rollback__create")
        self.graphs.complete_from_subagent({"session_id": "session-a", "task_graph_id": graph_id, "task_node_id": create_rollback["id"], "status": "completed", "result_preview": "done"})
        self.assertEqual(self.graphs.snapshot(graph_id, "session-a")["status"], "rolled_back")

        approval_graph = self.graphs.create("session-a", "approval", [{"id": "a", "objective": "a"}])
        node = approval_graph["nodes"][0]
        self.graphs.wait_for_approval(approval_graph["id"], node["id"], "session-a", ["ap_1"], "waiting")
        self.assertEqual(self.graphs.resolve_approval("ap_1", True, "session-a"), approval_graph["id"])
        self.assertEqual(self.graphs.snapshot(approval_graph["id"], "session-a")["nodes"][0]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
