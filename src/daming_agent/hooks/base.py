from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HookResult:
    """Hook 拦截控制结果。"""
    allowed: bool = True                                   # 是否允许继续执行
    message: str = ""                                      # 拒绝理由或拦截提示
    modified_arguments: Optional[dict[str, Any]] = None   # 修改后的工具入参（可选）


class BaseHook:
    """Agent 生命钩子基类 (Lifecycle Hook Base)。"""

    def before_chat(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """在请求大模型前触发。"""
        return messages

    def before_tool(self, tool_name: str, arguments: dict[str, Any]) -> HookResult:
        """在工具被真实执行之前触发。"""
        return HookResult(allowed=True)

    def after_tool(self, tool_name: str, arguments: dict[str, Any], result: str) -> str:
        """在工具真实执行完毕后触发。"""
        return result

    def after_chat(self, response: str) -> str:
        """在大模型完成最终回复后触发。"""
        return response
