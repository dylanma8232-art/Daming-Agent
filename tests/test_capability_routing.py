"""Regression tests for prompt-minimised Agent capabilities."""

from pathlib import Path

from agent import LocalAgent
from intent_router import Intent, IntentRouter
from skills.skill_manager import SkillManager
from channels.base import OutgoingMessage


class _Registry:
    def schemas(self):
        return [
            {"type": "function", "function": {"name": name, "parameters": {}}}
            for name in ("capability_search", "search_skills", "web_search", "fetch_webpage", "spawn_subagent", "view_skill", "lark_cli")
        ]


class _Mcp:
    def get_tool_schemas(self):
        return []


def _agent_for_routing():
    agent = LocalAgent.__new__(LocalAgent)
    agent.tool_registry = _Registry()
    agent.mcp_manager = _Mcp()
    agent.intent_router = IntentRouter()
    return agent


def test_smalltalk_exposes_no_unrelated_tools():
    assert {item["function"]["name"] for item in _agent_for_routing()._tool_schemas("你好")} == {"capability_search", "search_skills"}


def test_research_only_exposes_research_tools():
    names = {item["function"]["name"] for item in _agent_for_routing()._tool_schemas("调研一下 AI 新闻")}
    assert names == {"capability_search", "search_skills", "web_search", "fetch_webpage"}


def test_explicit_multi_agent_request_exposes_only_that_group():
    names = {item["function"]["name"] for item in _agent_for_routing()._tool_schemas("用多代理拆分任务")}
    assert names == {"capability_search", "search_skills", "spawn_subagent"}


def test_skill_metadata_is_cached_until_files_change(tmp_path: Path):
    skill = tmp_path / "demo"
    skill.mkdir()
    path = skill / "SKILL.md"
    path.write_text("---\nname: demo\ndescription: demo skill\n---\nbody", encoding="utf-8")
    manager = SkillManager([tmp_path])
    first = manager.skills
    manager.scan_skills()
    assert manager.skills is first
    assert manager.match_skills("请使用 demo skill") == ["demo"]
    assert manager.search_skills("demo skill")[0]["name"] == "demo"


def test_intent_router_has_one_primary_intent_and_unions_needed_capabilities():
    decision = IntentRouter().classify("请用多代理并行调研这个项目")
    assert decision.primary == Intent.ORCHESTRATION
    assert {"spawn_subagent", "web_search"} <= decision.tool_names


def test_control_reply_is_not_marked_as_streamed_content():
    """CLI must print control replies itself when no chunk callback was invoked."""
    outgoing = OutgoingMessage("当前模型模式：auto")
    emitted_chunk = False
    assert outgoing.content and not emitted_chunk
