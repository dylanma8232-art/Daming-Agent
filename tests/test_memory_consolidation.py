import unittest
from pathlib import Path
from memory import Memory

class TestMemoryConsolidationAndGraph(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path("data")
        self.memory = Memory(self.data_dir / "test_memories.json")

    def test_store_and_recall_flow(self):
        self.memory.store("用户偏好 Python", session_id="test_session")
        recalled = self.memory.recall("Python", session_id="test_session")
        self.assertTrue(len(recalled) >= 1)
        self.assertIn("用户偏好 Python", recalled[0])

if __name__ == "__main__":
    unittest.main()

