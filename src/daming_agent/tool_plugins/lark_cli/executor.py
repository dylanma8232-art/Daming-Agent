import subprocess
from typing import Any


READ_ONLY_ROOTS = {"schema", "skills", "whoami", "doctor"}


def run(arguments: dict[str, Any], *, session_id: str) -> str:
    """只暴露发现/诊断命令；业务写操作必须有独立、带风险声明的 Tool。"""
    argv = arguments.get("argv", [])
    if not isinstance(argv, list) or not argv or argv[0] not in READ_ONLY_ROOTS:
        return "lark_cli 当前仅允许 schema、skills、whoami、doctor 等只读发现命令。"
    try:
        result = subprocess.run(
            ["lark-cli", *[str(item) for item in argv]],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or result.stderr).strip()
        return output[:12000] or f"lark-cli 已结束，退出码 {result.returncode}。"
    except FileNotFoundError:
        return "未找到 lark-cli；请先安装并配置飞书 CLI。"
    except subprocess.TimeoutExpired:
        return "lark-cli 调用超时。"
