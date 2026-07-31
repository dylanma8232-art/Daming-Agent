import json
import os
import re
from pathlib import Path
from typing import Any, Optional
from config import AppConfig
from logger import get_logger

logger = get_logger("model_router")


class ModelRouter:
    """多模型动态路由器与容灾熔断中心：支持模型匹配、动态注册与超时自动降级切线。"""

    COMPLEX_KEYWORDS = {
        "重构", "架构", "debug", "测试", "实现", "设计", "算法", "分析",
        "refactor", "bug", "implement", "deploy", "task_graph"
    }

    SIMPLE_PATTERNS = [
        r"^(你好|在吗|哈喽|hello|hi|hey|安安|早上好|下午好|晚上好)[\!\?！？\s]*$",
        r"^(你是谁|你叫什么|你能做什么|自我介绍)[\!\?！？\s]*$",
        r"^(谢谢|感谢|OK|ok|收到|好的|行的|好的谢谢|再见)[\!\?！？\s]*$",
    ]

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.enabled = config.get("model.router_enabled", True)
        self.primary_model = os.getenv("CLOUD_MODEL", "") or config.get("model.primary_model", "qwen3.7-plus")
        self.fallback_model = os.getenv("CLOUD_FALLBACK_MODEL", "") or config.get("model.fallback_model", "kimi/kimi-k3")
        self.fast_model = os.getenv("CLOUD_FAST_MODEL", "") or config.get("model.fast_model", "qwen-turbo")
        ws_root = getattr(config, "workspace_root", getattr(config, "config_path", Path(".")).parent)
        self._dynamic_store_path = Path(ws_root) / "data" / "runtime" / "dynamic_models.json"

        self.dynamic_models: dict[str, dict[str, Any]] = self._load_dynamic_models()

    def _load_dynamic_models(self) -> dict[str, dict[str, Any]]:
        if self._dynamic_store_path.exists():
            try:
                return json.loads(self._dynamic_store_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"加载动态模型配置失败: {e}")
        return {}

    def _save_dynamic_models(self) -> None:
        try:
            self._dynamic_store_path.parent.mkdir(parents=True, exist_ok=True)
            self._dynamic_store_path.write_text(json.dumps(self.dynamic_models, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"保存动态模型配置失败: {e}")

    def register_model(self, alias: str, model_id: str, provider: str = "openai", api_base: str = "", api_key: str = "") -> dict[str, Any]:
        """动态注册/添加新模型并持久化落盘。"""
        alias_key = alias.strip().lower()
        record = {
            "alias": alias_key,
            "model_id": model_id.strip(),
            "provider": provider.strip(),
            "api_base": api_base.strip(),
            "api_key": api_key.strip(),
            "status": "active"
        }
        self.dynamic_models[alias_key] = record
        self._save_dynamic_models()
        logger.info(f"✨ [ModelRouter]: 成功动态注册新模型 [{alias_key}] -> {model_id}")
        return record

    def select_model(
        self,
        prompt: str,
        history: Optional[list[dict[str, Any]]] = None,
        retry_count: int = 0,
        forced_model: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        根据提示词、历史与重试状态评估并选择最佳模型。
        返回: (model_name, reasoning_summary)
        """
        if forced_model:
            return forced_model, "用户指定模型"
        if not self.enabled:
            return self.primary_model, "Router 已禁用，使用默认 Primary 模型"

        # 1. 重试机制：若连续出现重试，自动升级至 Flagship 备用模型
        if retry_count >= 1:
            reason = f"检测到请求重试 (第 {retry_count} 次)，自动熔断升级至 Flagship 备用模型"
            logger.info(f"🔀 [ModelRouter]: 评估匹配 -> {self.fallback_model} ({reason})")
            return self.fallback_model, reason

        text = (prompt or "").strip()

        # 2. 简单招呼/短回复问答 -> 切换至 Fast 轻量快速模型
        if len(text) < 20:
            for pattern in self.SIMPLE_PATTERNS:
                if re.match(pattern, text, re.IGNORECASE):
                    reason = "匹配简单招呼/短文本问答，分配 Fast 轻量快速模型"
                    logger.info(f"🔀 [ModelRouter]: 评估匹配 -> {self.fast_model} ({reason})")
                    return self.fast_model, reason

        # 3. 复杂任务 -> Primary 主力模型
        if any(kw in text.lower() for kw in self.COMPLEX_KEYWORDS) or "```" in text or len(text) > 300:
            reason = "检测到复杂任务关键词、代码块或长 Prompt，分配 Primary 主力模型"
            logger.info(f"🔀 [ModelRouter]: 评估匹配 -> {self.primary_model} ({reason})")
            return self.primary_model, reason

        # 4. 默认标准流程
        reason = "标准对话场景，分配 Primary 主力模型"
        logger.info(f"🔀 [ModelRouter]: 评估匹配 -> {self.primary_model} ({reason})")
        return self.primary_model, reason

    def available_models(self) -> dict[str, str]:
        """返回当前所有静态及动态注册的用户可用模型清单。"""
        models = {
            "primary": self.primary_model,
            "fast": self.fast_model,
            "fallback": self.fallback_model,
        }
        for alias, item in self.dynamic_models.items():
            models[alias] = item["model_id"]
        return models

    def get_fallback_model(self, current_model: str, attempted: list[str]) -> Optional[str]:
        """当模型超时、连接断开或 5xx 故障时，获取容灾链中的下一个可用备用模型。"""
        candidate_pool = [self.fallback_model, self.primary_model, self.fast_model]
        for dyn in self.dynamic_models.values():
            candidate_pool.append(dyn["model_id"])

        for model in candidate_pool:
            if model and model not in attempted and model != current_model:
                return model
        return None

    def resolve_model(self, selector: str) -> Optional[str]:
        """解析用户指定的模型别名或具体 Model ID。"""
        normalized = selector.strip().lower()
        aliases = {
            "primary": "primary", "主力": "primary", "默认": "primary",
            "fast": "fast", "快速": "fast",
            "fallback": "fallback", "备用": "fallback", "旗舰": "fallback",
        }
        models = self.available_models()
        if normalized in aliases:
            return models[aliases[normalized]]
        if normalized in models:
            return models[normalized]
        for model in models.values():
            if normalized == model.lower():
                return model
        return None

