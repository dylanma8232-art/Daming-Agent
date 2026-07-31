"""端到端引擎核心流程集成测试：验证 Hashline 防错、EnvLock 沙箱锁、模型感知与 Skill 扩展闭环。"""
import os
import shutil
import pytest
from pathlib import Path
from tools import LocalTools
from risk_policy import RiskPolicy
from runtime_store import RuntimeStore
from agent import LocalAgent
from intent_router import IntentRouter, Intent


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_hashline_editing_workflow(temp_workspace):
    """测试 1：Hashline 行哈希防改砸编辑完整流程"""
    tools = LocalTools(temp_workspace)
    test_file = temp_workspace / "code.py"
    test_file.write_text("def hello():\n    print('old')\n", encoding="utf-8")

    import hashlib
    target_text = "    print('old')"
    correct_hash = hashlib.md5(target_text.encode("utf-8")).hexdigest()[:8]

    # 正确 Hash 时替换成功
    res_success = tools.replace_file_content("code.py", target_text, "    print('new')", expected_hash=correct_hash)
    assert "成功精准替换" in res_success
    assert test_file.read_text(encoding="utf-8") == "def hello():\n    print('new')\n"

    # 错误 Hash 时拦截拒绝
    res_fail = tools.replace_file_content("code.py", "    print('new')", "    print('err')", expected_hash="wronghash")
    assert "❌ 替换拒绝：Hash 签名校验失败" in res_fail
    assert test_file.read_text(encoding="utf-8") == "def hello():\n    print('new')\n"


def test_envlock_sandbox_workflow(temp_workspace):
    """测试 2：EnvLock 物理沙箱目录锁定与拦截流程"""
    db_path = temp_workspace / "test_store.sqlite3"
    store = RuntimeStore(db_path)
    policy = RiskPolicy(store)

    core_dir = str(temp_workspace / "src" / "core")
    policy.lock_path(core_dir)

    # 验证受保护路径判断
    assert policy.is_path_locked(os.path.join(core_dir, "main.py")) is True
    assert policy.is_path_locked(str(temp_workspace / "readme.txt")) is False

    # 验证 check 函数拦截写操作
    allowed, msg, _, risk = policy.check("write_file", {"relative_path": os.path.join(core_dir, "main.py")}, session_id="s1")
    assert allowed is False
    assert "🛑 物理沙箱拦截" in msg
    assert "EnvLock" in msg


def test_model_awareness_routing_workflow():
    """测试 3：自然语言模型询问路由闭环"""
    router = IntentRouter()
    decision = router.classify("你当前用的是什么模型？")
    assert decision.primary == Intent.MODEL_CONTROL


def test_skill_creation_intent_routing_workflow():
    """测试 4：自然语言增加技能路由与工具授权闭环"""
    router = IntentRouter()
    decision = router.classify("帮我新建一个提取日志的 skill")
    assert decision.primary == Intent.EXTERNAL_CAPABILITY
    assert "write_file" in decision.tool_names
    assert "acquire_external_skill" in decision.tool_names


def test_hierarchical_supervisor_workflow(temp_workspace):
    """测试 5：Hierarchical Supervisor 分层主从治理任务图生成流程"""
    from task_graph import TaskGraphManager
    db_path = temp_workspace / "test_store.sqlite3"
    store = RuntimeStore(db_path)
    tg = TaskGraphManager(store)

    graph = tg.create_supervisor_governance_graph(
        session_id="s1",
        title="系统重构架构",
        supervisor_objective="完成模块重构",
        worker_tasks=[
            {"id": "w1", "objective": "编写核心逻辑", "role": "executor"},
            {"id": "w2", "objective": "编写自动化测试", "role": "executor", "depends_on": ["w1"]}
        ]
    )

    assert graph["id"].startswith("graph_")
    # 包含了 supervisor_plan, w1, w2, auditor_review 4个节点
    nodes = graph["nodes"]
    assert len(nodes) == 4
    roles = [n["role"] for n in nodes]
    assert "supervisor" in roles
    assert "reviewer" in roles

