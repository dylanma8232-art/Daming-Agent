import tempfile
import unittest
from pathlib import Path

from runtime_store import RuntimeStore


class RuntimeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.store = RuntimeStore(Path(tempfile.mkdtemp()) / "runtime")

    def test_startup_interrupts_only_unfinished_runs(self):
        self.store.run("unfinished", session_id="a", status="running", objective="work")
        self.store.run("answered", session_id="a", status="running", answer_preview="already sent")

        records = {row["id"]: row for row in self.store.interrupt_unfinished_runs("restart")}

        self.assertEqual(records["unfinished"]["status"], "interrupted")
        self.assertEqual(records["answered"]["status"], "completed")
        self.assertEqual(self.store.data["runs"]["answered"]["answer_preview"], "already sent")

    def test_terminal_run_cannot_be_overwritten_by_recovery_or_late_worker(self):
        self.store.run("done", session_id="a", status="running")
        self.assertTrue(self.store.finish_run("done", "completed", answer_preview="reply"))
        self.assertFalse(self.store.finish_run("done", "interrupted", recovery_note="restart"))
        self.store.interrupt_unfinished_runs("restart")
        record = self.store.data["runs"]["done"]
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["answer_preview"], "reply")


if __name__ == "__main__":
    unittest.main()
