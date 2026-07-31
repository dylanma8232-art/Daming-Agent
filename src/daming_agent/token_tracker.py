import json
from pathlib import Path
from typing import Any, Optional


class TokenTracker:
    """全局 Token 消耗统计与多维归因分析器。"""

    def __init__(self, base_dir: Path) -> None:
        self.file_path = (base_dir / "data" / "token_usage.json").resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return self._empty_structure()
        try:
            content = self.file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return data if isinstance(data, dict) else self._empty_structure()
        except Exception as e:
            print(f"⚠️ 读取 Token 统计文件失败 ({e})，重新初始化。")
            return self._empty_structure()

    def _save(self) -> None:
        try:
            self.file_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"⚠️ 保存 Token 统计文件失败: {e}")

    @staticmethod
    def _empty_structure() -> dict[str, Any]:
        return {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_requests": 0,
            "by_session": {},
            "by_model": {},
        }

    def add_usage(
        self,
        session_id: str = "default",
        model: str = "unknown",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """记录一次 LLM 请求的 Token 消耗。"""
        total = prompt_tokens + completion_tokens

        # 1. 累计全局总量
        self.data["total_prompt_tokens"] += prompt_tokens
        self.data["total_completion_tokens"] += completion_tokens
        self.data["total_tokens"] += total
        self.data["total_requests"] += 1

        # 2. 按 Session 归因统计
        session_stats = self.data["by_session"].get(
            session_id, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}
        )
        session_stats["prompt_tokens"] += prompt_tokens
        session_stats["completion_tokens"] += completion_tokens
        session_stats["total_tokens"] += total
        session_stats["requests"] += 1
        self.data["by_session"][session_id] = session_stats

        # 3. 按 Model 归因统计
        model_stats = self.data["by_model"].get(
            model, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}
        )
        model_stats["prompt_tokens"] += prompt_tokens
        model_stats["completion_tokens"] += completion_tokens
        model_stats["total_tokens"] += total
        model_stats["requests"] += 1
        self.data["by_model"][model] = model_stats

        # 4. 持久化落盘
        self._save()

    def get_summary(self, session_id: Optional[str] = None) -> dict[str, Any]:
        """获取 Token 消耗统计摘要。"""
        res = {
            "global_totals": {
                "total_prompt_tokens": self.data["total_prompt_tokens"],
                "total_completion_tokens": self.data["total_completion_tokens"],
                "total_tokens": self.data["total_tokens"],
                "total_requests": self.data["total_requests"],
            },
            "by_model": self.data["by_model"],
        }
        if session_id:
            res["session_stats"] = self.data["by_session"].get(
                session_id, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}
            )
        return res
