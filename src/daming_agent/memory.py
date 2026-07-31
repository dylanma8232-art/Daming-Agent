import json
import os
import re
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

# 设置全局忽略 macOS 的 urllib SSL 证书验证报错
ssl._create_default_https_context = ssl._create_unverified_context



import json
import os
import re
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

# 设置全局忽略 macOS 的 urllib SSL 证书验证报错
ssl._create_default_https_context = ssl._create_unverified_context


class Memory:
    """标准生产级记忆框架：支持会话隔离与关键字索引召回。"""

    def __init__(self, path: Path, backend: str = "json") -> None:
        self.path = path
        self.backend = backend
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def before_turn(self, user_input: str, session_id: str = "default", agent_id: str = "agent", tenant_id: Optional[str] = None) -> list[str]:
        """在 Turn 开始前召回与当前输入相关的长期记忆。"""
        return self.recall(user_input, session_id=session_id)

    def after_turn(self, user_input: str, output: str, session_id: str = "default", agent_id: str = "agent", tenant_id: Optional[str] = None) -> None:
        """在 Turn 完成后保存本轮会话记忆摘要。"""
        if user_input and output:
            summary_text = f"用户: {user_input[:200]}\n回答: {output[:300]}"
            self.store(summary_text, session_id=session_id, agent_id=agent_id, tenant_id=tenant_id)

    def save_history(self, session_id: str, history: list[dict[str, Any]]) -> None:
        """按 session_id 隔离持久化保存短期对话历史。"""
        sessions_dir = self.path.parent / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = sessions_dir / f"{session_id}.json"
        try:
            # 只保留最近 50 轮消息到磁盘文件中，保证读写效率与安全性
            session_file.write_text(json.dumps(history[-100:], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def load_history(self, session_id: str) -> list[dict[str, Any]]:
        """按 session_id 读取保存的短期对话历史。"""
        session_file = self.path.parent / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return []
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def clear_history(self, session_id: str) -> None:
        """清空指定 session_id 的对话历史文件。"""
        session_file = self.path.parent / "sessions" / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
            except OSError:
                pass

    def on_tool_call(self, tool_name: str, arguments: Any, result_preview: str, session_id: str = "default", agent_id: str = "agent", tenant_id: Optional[str] = None) -> None:
        """工具调用完成后的日志钩子。"""
        pass

    def compact_context(self, session_id: str = "default", max_tokens: int = 4000, keep_turns: int = 10) -> list[dict[str, Any]]:
        """上下文压缩规约。"""
        return []

    def on_error(self, error: Exception, session_id: str = "default", agent_id: str = "agent", tenant_id: Optional[str] = None) -> None:
        """运行报错事件钩子。"""
        pass

    def store(self, text: str, session_id: str = "default", agent_id: str = "agent", tenant_id: Optional[str] = None) -> None:
        memories = self._read()
        if any(item.get("text") == text and item.get("session_id") == session_id for item in memories):
            return
        memories.append({"text": text, "session_id": session_id, "saved_at": datetime.now(UTC).isoformat()})
        self._write(memories[-200:])

    def recall(self, query: str, limit: int = 3, session_id: str = "default", tenant_id: Optional[str] = None) -> list[str]:
        query_words = self._keywords(query)
        scored: list[tuple[int, str]] = []
        for item in self._read():
            if item.get("session_id") and item.get("session_id") != session_id:
                continue
            text = item.get("text", "")
            score = sum(word in text.lower() for word in query_words)
            if score:
                scored.append((score, text))
        return [text for _, text in sorted(scored, reverse=True)[:limit]]

    def get_all(self, session_id: str = "default") -> list[dict[str, str]]:
        return [item for item in self._read() if not item.get("session_id") or item.get("session_id") == session_id]

    def _read(self) -> list[dict[str, str]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, content: list[dict[str, str]]) -> None:
        self.path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _keywords(text: str) -> set[str]:
        words = set(re.findall(r"[a-zA-Z0-9_]{2,}", text.lower()))
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", text))
        words.update(chinese[index : index + 2] for index in range(len(chinese) - 1))
        return words


