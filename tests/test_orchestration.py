import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from orchestration import CronManager, SubagentManager, is_due, validate_schedule
from runtime_store import RuntimeStore


class OrchestrationTests(unittest.TestCase):
    def setUp(self): self.store = RuntimeStore(Path(tempfile.mkdtemp()) / "runtime")

    def test_subagent_is_session_isolated_and_runs(self):
        manager = SubagentManager(self.store, lambda objective, session: f"{session}:{objective}", max_workers=2)
        row = manager.spawn("session-a", "research", "researcher")
        for _ in range(20):
            current = self.store.get_subagent(row["id"], "session-a")
            if current["status"] == "completed": break
            time.sleep(.02)
        self.assertEqual(current["status"], "completed")
        self.assertIn("session-a::subagent", current["result_preview"])
        self.assertIsNone(self.store.get_subagent(row["id"], "session-b"))

    def test_cron_persists_and_executes_in_isolated_session(self):
        called = []
        manager = CronManager(self.store, lambda prompt, session: called.append((prompt, session)) or "done", poll_seconds=60)
        try:
            row = manager.create("session-a", "fast", "every:1", "check status")
            self.assertEqual(manager.tick(now=10), [row["id"]])
            for _ in range(20):
                if called: break
                time.sleep(.02)
            self.assertEqual(called[0][1], f"session-a::cron::{row['id']}")
            self.assertEqual(manager.tick(now=10.5), [])
            self.assertTrue(manager.set_status(row["id"], "session-a", False))
            self.assertEqual(self.store.get_cron_job(row["id"], "session-a")["status"], "paused")
        finally: manager.stop()

    def test_cron_expression_validation(self):
        validate_schedule("0 9 * * *")
        validate_schedule("every:30")
        self.assertTrue(is_due("0 9 * * *", 0, datetime(2026, 1, 1, 9, 0).timestamp()))
        with self.assertRaises(ValueError): validate_schedule("invalid")


if __name__ == "__main__": unittest.main()
