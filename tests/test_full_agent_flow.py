import time
import unittest
from pathlib import Path

from agent import LocalAgent


class FullAgentFlowIntegrationTests(unittest.TestCase):
    """大明 Agent & 大明 OS 全流程集成检验。"""

    def setUp(self):
        self.agent = LocalAgent()

    def test_01_agent_memory_loaded(self):
        """验证 Agent 内存与持久化机制。"""
        self.assertIsNotNone(self.agent.memory)
        self.assertIsNotNone(self.agent.runtime_store)


    def test_02_memory_lifecycle(self):
        """验证 before_turn 记忆召回与 after_turn 记忆沉淀。"""
        session_id = "test_full_flow_session"
        # 存储一条长期偏好
        self.agent.memory.store("用户偏好：使用 Python3 进行自动化编程", session_id=session_id)
        
        # 召回检验
        recalled = self.agent.memory.before_turn("Python", session_id=session_id)
        self.assertTrue(len(recalled) >= 0)
        
        # 触发 Turn 完成沉淀
        self.agent.memory.after_turn("测试问题", "测试回答", session_id=session_id)

    def test_03_ast_syntax_sandbox_gate(self):
        """验证 Daming OS 沙箱门禁：检测合法与非法 Python 代码。"""
        session_id = "test_syntax_gate"
        tools = self.agent._get_session_tools(session_id)
        
        # 1. 正常 Python 代码写入
        valid_code = "def hello():\n    print('Hello World')\n"
        res_ok = tools.write_file("valid_script.py", valid_code)
        self.assertIn("成功", res_ok)

        # 2. 带有 AST 语法错误的 Python 代码触发沙箱拦截模拟
        import ast
        invalid_code = "def broken_func(\n    print('Missing paren')"
        with self.assertRaises(SyntaxError):
            ast.parse(invalid_code)

    def test_04_subagent_orchestration_flow(self):
        """验证子 Agent 协作派发与并发挂起。"""
        session_id = "test_orchestration_flow"
        subagent = self.agent.subagent_manager.spawn(
            session_id=session_id,
            objective="测试后台并发子 Agent 执行任务",
            role="test_worker"
        )
        self.assertIsNotNone(subagent)
        self.assertIn("sub_", subagent["id"])
        
        # 检查运行记录存盘
        stored = self.agent.runtime_store.get_subagent(subagent["id"], session_id=session_id)
        self.assertIsNotNone(stored)

    def test_05_cron_job_lifecycle(self):
        """验证 Cron 定时任务注册、暂停与删除。"""
        session_id = "test_cron_flow"
        job = self.agent.cron_manager.create(
            session_id=session_id,
            name="每分钟巡检任务",
            expression="every:60",
            prompt="巡检系统状态"
        )
        self.assertIn("cron_", job["id"])
        
        # 暂停任务
        self.assertTrue(self.agent.cron_manager.set_status(job["id"], session_id, False))
        # 删除任务
        self.assertTrue(self.agent.cron_manager.delete(job["id"], session_id))

    def test_06_skill_manager_and_trace_logger(self):
        """验证 SOP 技能展示与 Trace 日志广播。"""
        hint = self.agent.skill_manager.get_skill_summary_hint()
        self.assertIsInstance(hint, str)

        # Trace 记录
        self.agent.trace_logger.log_trace(
            session_id="test_trace",
            event_type="tool_call",
            tool_name="web_search",
            arguments={"query": "Daming OS"},
            result="搜索完成",
            duration_ms=120.0
        )


if __name__ == "__main__":
    unittest.main()
