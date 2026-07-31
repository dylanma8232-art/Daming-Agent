import json
import time
from pathlib import Path
from typing import Any, Optional


class TraceLogger:
    """性能与工具调用追踪日志记录器 (OpenTelemetry 兼容格式)。"""

    def __init__(self, base_dir: Path) -> None:
        self.traces_dir = (base_dir / "data" / "traces").resolve()
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def log_trace(
        self,
        session_id: str,
        event_type: str,
        tool_name: Optional[str] = None,
        arguments: Optional[dict[str, Any]] = None,
        result: Optional[str] = None,
        duration_ms: Optional[float] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """记录标准 Trace 日志文件。"""
        trace_file = self.traces_dir / f"{session_id}_trace.jsonl"
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "session_id": session_id,
            "event_type": event_type,
            "tool_name": tool_name,
            "arguments": arguments,
            "result_preview": str(result)[:300] if result is not None else None,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "extra": extra,
        }
        try:
            with trace_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ 写入 Trace 日志失败: {e}")



