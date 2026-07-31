from typing import Any
from hooks.base import BaseHook, HookResult


class HookManager:
    """管理生命周期 Hook 钩子的注册与广播调度。"""

    def __init__(self) -> None:
        self.hooks: list[BaseHook] = []

    def register_hook(self, hook: BaseHook) -> None:
        self.hooks.append(hook)

    def trigger_before_chat(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        current_messages = messages
        for hook in self.hooks:
            try:
                current_messages = hook.before_chat(current_messages)
            except Exception as e:
                print(f"⚠️ [Hook Error in {hook.__class__.__name__}.before_chat]: {e}")
        return current_messages

    def trigger_before_tool(self, tool_name: str, arguments: dict[str, Any]) -> HookResult:
        for hook in self.hooks:
            try:
                res = hook.before_tool(tool_name, arguments)
                if not res.allowed:
                    return res
            except Exception as e:
                print(f"⚠️ [Hook Error in {hook.__class__.__name__}.before_tool]: {e}")
        return HookResult(allowed=True)

    def trigger_after_tool(self, tool_name: str, arguments: dict[str, Any], result: str) -> str:
        current_result = result
        for hook in self.hooks:
            try:
                current_result = hook.after_tool(tool_name, arguments, current_result)
            except Exception as e:
                print(f"⚠️ [Hook Error in {hook.__class__.__name__}.after_tool]: {e}")
        return current_result

    def trigger_after_chat(self, response: str) -> str:
        current_response = response
        for hook in self.hooks:
            try:
                current_response = hook.after_chat(current_response)
            except Exception as e:
                print(f"⚠️ [Hook Error in {hook.__class__.__name__}.after_chat]: {e}")
        return current_response
