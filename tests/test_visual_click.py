import unittest
from tools import LocalTools
from pathlib import Path

class TestVisualClick(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        self.tools = LocalTools(self.workspace)

    def test_click_visual_without_open_browser(self):
        result = self.tools.click_visual("测试点击", 0.5, 0.5, session_id="test_visual_session")
        self.assertIn("浏览器尚未打开", result)

if __name__ == "__main__":
    unittest.main()
