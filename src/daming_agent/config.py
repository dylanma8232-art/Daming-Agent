import os
from pathlib import Path
from typing import Any, Optional
import yaml


class AppConfig:
    """Agent 统一配置管理与加载器。"""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parent / "agent.config.yaml"
        self.config_path = config_path.resolve()
        self.data: dict[str, Any] = self._load_yaml()

    def _load_yaml(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return self._default_config()
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content if isinstance(content, dict) else self._default_config()
        except Exception as e:
            print(f"⚠️ 加载配置文件 {self.config_path} 失败: {e}，将使用默认配置。")
            return self._default_config()

    def get(self, key_path: str, default: Any = None) -> Any:
        """支持形如 'model.primary_model' 的点分隔路径读取配置。"""
        keys = key_path.split(".")
        val: Any = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    @staticmethod
    def _default_config() -> dict[str, Any]:
        return {
            "agent": {
                "name": "Daming Agent",
                "timeout": 30,
            },
            "model": {
                "primary_model": os.getenv("CLOUD_MODEL", "qwen-plus"),
                "max_retries": 3,
            },
            "context": {
                "max_token_budget": 8000,
                "auto_summarize": True,
            },
            "browser": {"headless": True, "slow_mo_ms": 80},
            "sessions": {"channels": {}},
            "skills": {"enabled": True, "roots": ["skills", ".agents/skills"]},
            "mcp": {"enabled": True, "servers": []},
        }
