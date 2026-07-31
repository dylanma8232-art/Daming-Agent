import unittest
from tools import LocalTools
from pathlib import Path

class TestWebSearchAggregator(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        self.tools = LocalTools(self.workspace)

    def test_web_search_empty_query(self):
        res = self.tools.web_search("")
        self.assertIn("不能为空", res)

    def test_web_search_real_query(self):
        res = self.tools.web_search("Python 编程语言")
        self.assertTrue(isinstance(res, str))
        self.assertTrue("网址" in res or "未找到" in res or "搜索引擎" in res)

if __name__ == "__main__":
    unittest.main()
