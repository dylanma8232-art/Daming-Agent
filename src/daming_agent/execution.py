"""将历史字符串式工具返回统一为可审计、可验证的执行结果。"""
import json
import re
from pathlib import Path
from typing import Any


def normalize(tool_name: str, arguments: dict[str, Any], raw: Any, workspace: Path) -> dict[str, Any]:
    text = str(raw)
    lowered = text.lower()
    failed = any(marker in lowered for marker in ("失败", "错误", "异常", "拒绝", "不存在", "unknown tool", "mcp 工具调用失败"))
    verification: dict[str, Any] = {"passed": not failed, "kind": "response", "detail": "工具返回已接收"}
    artifacts: list[str] = []
    relative = arguments.get("relative_path")
    if tool_name in {"write_file", "append_file", "replace_file_content", "create_word_document", "create_ppt_presentation", "create_pdf_document", "create_excel_spreadsheet", "screenshot"} and relative:
        try:
            candidate = (workspace / relative).resolve()
            exists = candidate.is_file() and workspace.resolve() in candidate.parents
            verification = {"passed": exists and not failed, "kind": "file_exists", "detail": str(candidate) if exists else "预期产物不存在"}
            if exists: artifacts.append(str(candidate))
        except Exception:
            verification = {"passed": False, "kind": "file_exists", "detail": "产物路径不安全"}
    elif tool_name == "run_command":
        match = re.search(r"退出码[:：]?\s*(-?\d+)", text)
        code = int(match.group(1)) if match else None
        verification = {"passed": not failed and (code in (None, 0)), "kind": "exit_code", "detail": f"exit_code={code}" if code is not None else "未提供退出码"}
    elif tool_name in {"open_browser", "click", "type_text"}:
        verification = {"passed": not failed, "kind": "page_state", "detail": "浏览器操作返回成功" if not failed else text[:200]}
    elif tool_name.startswith("mcp_"):
        verification = {"passed": not failed, "kind": "mcp_response", "detail": "MCP 已确认响应" if not failed else text[:200]}
    if '"screenshot_result"' in text:
        try:
            payload = json.loads(text)
            screenshot_path = payload.get("path") or payload.get("relative_path")
            if screenshot_path: artifacts.append(str((workspace / screenshot_path).resolve()))
        except Exception: pass
    status = "succeeded" if verification["passed"] else "failed"
    return {"status": status, "summary": text[:1000], "artifacts": artifacts, "verification": verification, "retryable": status == "failed" and tool_name not in {"write_file", "append_file", "replace_file_content"}, "error": None if status == "succeeded" else text[:500]}
