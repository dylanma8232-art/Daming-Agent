import json
from typing import Any, Callable, Optional


class ContextManager:
    """上下文 Token 预算管理与自动摘要压缩器。"""

    def __init__(self, max_token_budget: int = 8000, auto_summarize: bool = True) -> None:
        self.max_token_budget = max_token_budget
        self.auto_summarize = auto_summarize

    @staticmethod
    def estimate_tokens(messages: list[dict[str, Any]]) -> int:
        """估算消息列表消耗的 Token 总量 (中文字符~0.6 Token, 英文字符~0.3 Token)。"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 2 + 10
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        total += len(item.get("text", "")) // 2 + 10
                    elif item.get("type") == "image_url":
                        total += 500  # 图像算作固定预算
        return total

    @classmethod
    def estimate_request_tokens(cls, messages: list[dict[str, Any]], tools: Optional[list[dict[str, Any]]] = None) -> int:
        """Estimate the whole model request, including function schemas.

        The provider is the final authority, but tool schemas used to be
        invisible to the Agent's budget and could silently consume most of the
        context window.
        """
        tool_text = json.dumps(tools or [], ensure_ascii=False, separators=(",", ":"))
        return cls.estimate_tokens(messages) + (len(tool_text) // 2 + 10 if tool_text != "[]" else 0)

    def manage_context(
        self,
        messages: list[dict[str, Any]],
        summarize_func: Optional[Callable[[str], str]] = None,
    ) -> list[dict[str, Any]]:
        """当 Token 接近预算上限时，自动截取并压缩旧历史消息。"""
        current_tokens = self.estimate_tokens(messages)
        if current_tokens <= self.max_token_budget:
            return messages

        print(f"⚡ [ContextManager] 上下文 Token ({current_tokens}) 超过预算 ({self.max_token_budget})，正在触发自动摘要压缩...")

        # 保护系统消息和最新的 4 条消息
        system_msg = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        if len(other_msgs) <= 4:
            return messages

        old_msgs = other_msgs[:-4]
        recent_msgs = other_msgs[-4:]

        if self.auto_summarize and summarize_func:
            old_text = "\n".join(f"{m['role']}: {str(m['content'])[:100]}" for m in old_msgs)
            try:
                summary = summarize_func(f"请用两三句话总结以下早期对话核心要点：\n{old_text}")
                summary_msg = {
                    "role": "system",
                    "content": f"[早期历史对话摘要总结]: {summary}"
                }
                return system_msg + [summary_msg] + recent_msgs
            except Exception as e:
                print(f"⚠️ 自动摘要生成失败: {e}")

        # 降级方案：直接对旧消息进行切片截断
        return system_msg + recent_msgs
