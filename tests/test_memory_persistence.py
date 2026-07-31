import tempfile
import os
import uuid
from pathlib import Path
from memory import Memory
from agent import LocalAgent


def test_session_history_persists_across_restarts():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DAMING_RUNTIME_DIR"] = tmpdir
        
        session_id = f"test_session_{uuid.uuid4().hex}"
        
        # 1. 模拟第一次启动 LocalAgent 并进行对话
        agent1 = LocalAgent()
        agent1.memory.clear_history(session_id)
        
        # 保存对话历史
        history1 = agent1._get_session_history(session_id)
        history1.extend([
            {"role": "user", "content": "你好，我是大明"},
            {"role": "assistant", "content": "你好大明，很高兴为你服务！"},
        ])
        agent1.memory.save_history(session_id, history1)
        agent1.memory.after_turn("你好，我是大明", "你好大明，很高兴为你服务！", session_id=session_id)
        
        # 2. 模拟服务重启：重新实例化 LocalAgent
        agent2 = LocalAgent()
        
        # 验证 agent2 成功从磁盘读回了之前的会话历史
        restored_history = agent2._get_session_history(session_id)
        assert len(restored_history) == 2
        assert restored_history[0]["content"] == "你好，我是大明"
        assert restored_history[1]["content"] == "你好大明，很高兴为你服务！"
        
        # 验证长期记忆 recall 也正常保存并成功召回
        recalled = agent2.memory.recall("大明", session_id=session_id)
        assert len(recalled) > 0
        assert "大明" in recalled[0]
        
        # 清理测试数据
        agent2.memory.clear_history(session_id)
