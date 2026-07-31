"""统一风险分级：本地 workspace 写入自动执行，外部/高风险必须审批。"""
import uuid
import os
from typing import Any
from runtime_store import RuntimeStore


LOCAL_WRITE_TOOLS = {"write_file", "append_file", "replace_file_content", "create_word_document", "create_ppt_presentation", "create_pdf_document", "create_excel_spreadsheet", "screenshot", "run_command", "run_command_async"}
HIGH_RISK_WORDS = (" rm ", "rm -", "rmdir", "kill ", "pkill", "git push", "npm publish", "pip publish", "curl ", "wget ", "ssh ", "scp ", "open ", " task delete", " rollback full", " rollback-full", " hook-install")


class RiskPolicy:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store
        self.read_only_mcp_tools: set[str] = set()
        self.locked_paths: set[str] = set()

    def set_read_only_mcp_tools(self, names: set[str]) -> None:
        self.read_only_mcp_tools = set(names)

    def lock_path(self, path: str) -> None:
        """物理锁定指定目录/路径，禁止写入或改动。"""
        if path:
            self.locked_paths.add(os.path.normpath(path))

    def unlock_path(self, path: str) -> None:
        """解锁指定目录/路径。"""
        if path:
            self.locked_paths.discard(os.path.normpath(path))

    def is_path_locked(self, target_path: str) -> bool:
        """检查路径是否落入受排他保护的锁定目录。"""
        if not target_path or not self.locked_paths:
            return False
        norm_target = os.path.normpath(target_path)
        for locked in self.locked_paths:
            if norm_target == locked or norm_target.startswith(locked + os.sep):
                return True
        return False

    def classify(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name.startswith("mcp_"):
            return "read" if tool_name in self.read_only_mcp_tools else "external_write"
        if tool_name in {"send_message", "lark_cli"}:
            return "external_write"
        if tool_name in {"kill_task", "cancel_subagent", "rollback_task_graph"}: return "high_risk"
        if tool_name in {"run_command", "run_command_async"}:
            command = f" {arguments.get('command', '').lower()} "
            return "high_risk" if any(word in command for word in HIGH_RISK_WORDS) else "local_write"
        if tool_name in LOCAL_WRITE_TOOLS: return "local_write"
        return "read"

    def check(self, tool_name: str, arguments: dict[str, Any], session_id: str, run_id: str | None = None) -> tuple[bool, str, str | None, str]:
        # 物理路径锁定门控逻辑 (EnvLock)
        target_path = arguments.get("relative_path") or arguments.get("target_path") or arguments.get("path", "")
        if target_path and tool_name in LOCAL_WRITE_TOOLS:
            if self.is_path_locked(str(target_path)):
                return False, f"🛑 物理沙箱拦截：路径 '{target_path}' 已被环境锁锁定 (EnvLock)，禁止写入或改动！", None, "high_risk"

        risk = self.classify(tool_name, arguments)
        if risk in {"read", "local_write"}: return True, "", None, risk
        approval_id = "ap_" + uuid.uuid4().hex
        self.store.request_approval(approval_id, session_id=session_id, run_id=run_id, tool_name=tool_name, arguments=arguments, risk=risk, replay_count=0)
        return False, f"此操作属于 {risk}，已进入审批队列，审批编号: {approval_id}", approval_id, risk

