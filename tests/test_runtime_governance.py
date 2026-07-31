import tempfile
import time
import unittest
from pathlib import Path

from execution import normalize
from risk_policy import RiskPolicy
from runtime_store import RuntimeStore
from tools import TaskManager


class RuntimeGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = RuntimeStore(self.root / "runtime")

    def test_local_write_is_automatic_external_is_pending_and_redacted(self):
        policy = RiskPolicy(self.store)
        allowed, _, _, risk = policy.check("write_file", {"relative_path": "a.txt"}, "alpha")
        self.assertTrue(allowed); self.assertEqual(risk, "local_write")
        allowed, _, approval_id, risk = policy.check("mcp_feishu_send", {"token": "do-not-leak"}, "alpha")
        self.assertFalse(allowed); self.assertEqual(risk, "external_write")
        approval = self.store.approvals("alpha")[0]
        self.assertEqual(approval["id"], approval_id)
        self.assertEqual(approval["arguments"]["token"], "***")
        self.assertIsNotNone(self.store.claim_approval(approval_id, True))
        self.assertIsNone(self.store.claim_approval(approval_id, True))

    def test_task_persists_completes_and_is_session_isolated(self):
        manager = TaskManager(self.root / "workspace", self.store, "alpha")
        started = manager.run_command_async('python3 -c "print(123)"')
        task_id = started.split("[")[1].split("]")[0]
        time.sleep(0.3)
        self.assertIn("completed", manager.list_tasks())
        self.assertIsNotNone(self.store.get_task(task_id, "alpha"))
        self.assertIsNone(self.store.get_task(task_id, "beta"))

    def test_recovery_never_replays_dead_task(self):
        workspace = self.root / "workspace"
        self.store.task("dead", session_id="alpha", workspace=str(workspace), command="unsafe", pid=99999999, status="running")
        TaskManager(workspace, self.store, "alpha")
        self.assertEqual(self.store.get_task("dead", "alpha")["status"], "interrupted")

    def test_run_recovery_is_terminal_and_never_overwrites_a_persisted_reply(self):
        """A restart must not leave yesterday's completed reply runnable again."""
        self.store.run("reply-ready", session_id="alpha", status="running", answer_preview="already sent")
        self.store.run("unfinished", session_id="alpha", status="running")

        recovered = {row["id"]: row for row in self.store.interrupt_unfinished_runs("restart")}

        self.assertEqual(recovered["reply-ready"]["status"], "completed")
        self.assertEqual(recovered["unfinished"]["status"], "interrupted")
        self.assertFalse(self.store.finish_run("reply-ready", "interrupted"))
        self.assertEqual(self.store.data["runs"]["reply-ready"]["status"], "completed")

    def test_execution_verifies_file_and_command(self):
        workspace = self.root / "workspace"; workspace.mkdir()
        (workspace / "ok.txt").write_text("ok")
        file_result = normalize("write_file", {"relative_path": "ok.txt"}, "成功写入", workspace)
        self.assertEqual(file_result["status"], "succeeded")
        command_result = normalize("run_command", {}, "命令执行完成，退出码: 1", workspace)
        self.assertEqual(command_result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
