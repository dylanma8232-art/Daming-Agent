import unittest
from pathlib import Path
from config import AppConfig
from model_router import ModelRouter


class TestModelRouter(unittest.TestCase):
    """测试 ModelRouter 动态选型逻辑。"""

    def setUp(self):
        self.base_dir = Path(__file__).parent.parent
        self.config = AppConfig(self.base_dir / "agent.config.yaml")
        self.router = ModelRouter(self.config)

    def test_simple_greeting_selects_fast_model(self):
        model, reason = self.router.select_model("你好！", retry_count=0)
        self.assertEqual(model, self.router.fast_model)
        self.assertIn("Fast", reason)

        model2, _ = self.router.select_model("谢谢", retry_count=0)
        self.assertEqual(model2, self.router.fast_model)

    def test_complex_keyword_selects_primary_model(self):
        model, reason = self.router.select_model("帮我重构这段代码的架构", retry_count=0)
        self.assertEqual(model, self.router.primary_model)
        self.assertIn("Primary", reason)

    def test_code_block_selects_primary_model(self):
        code_prompt = "```python\ndef foo(): pass\n```"
        model, _ = self.router.select_model(code_prompt, retry_count=0)
        self.assertEqual(model, self.router.primary_model)

    def test_retry_count_upgrades_to_flagship_model(self):
        model, reason = self.router.select_model("简单回答", retry_count=1)
        self.assertEqual(model, self.router.fallback_model)
        self.assertIn("Flagship", reason)

    def test_forced_model_overrides_auto_routing(self):
        model, reason = self.router.select_model("你好", forced_model=self.router.primary_model)
        self.assertEqual(model, self.router.primary_model)
        self.assertIn("指定模型", reason)

    def test_dynamic_model_registration_and_failover(self):
        # 1. 验证动态注册模型
        rec = self.router.register_model("deepseek-r1", "deepseek-reasoner", provider="deepseek")
        self.assertEqual(rec["alias"], "deepseek-r1")
        self.assertEqual(self.router.resolve_model("deepseek-r1"), "deepseek-reasoner")

        # 2. 验证超时/断开故障降级容灾链
        fallback = self.router.get_fallback_model("qwen3.7-plus", attempted=["qwen3.7-plus"])
        self.assertIsNotNone(fallback)
        self.assertNotEqual(fallback, "qwen3.7-plus")


if __name__ == "__main__":
    unittest.main()

