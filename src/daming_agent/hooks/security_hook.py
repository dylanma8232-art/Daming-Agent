import re
from typing import Any
from hooks.base import BaseHook, HookResult


class SecurityHook(BaseHook):
    """安全风控 Hook：自动拦截本地高危命令与破坏性路径操作。"""

    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+\*",
        r"mkfs",
        r"dd\s+if=",
        r">:|\(\)\{\s*:\|:&\s*\}",  # Fork bomb
        r"chmod\s+-R\s+777\s+/",
    ]

    def before_tool(self, tool_name: str, arguments: dict[str, Any]) -> HookResult:
        if tool_name in ("run_command", "run_command_async"):
            command = arguments.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    print(f"🛡️ [SecurityHook 安全拦截] 监测到高危指令: '{command}'")
                    return HookResult(
                        allowed=False,
                        message=f"🛡️ [安全拦截引擎]: 拒绝执行包含潜在破坏性指令的 Shell 命令 ('{command}')。"
                    )
        return HookResult(allowed=True)
