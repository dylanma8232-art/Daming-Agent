import time
from typing import Any, Callable, Optional
import httpx


class RetryPolicy:
    """指数退避网络重试与工具自省反馈策略。"""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def execute_with_retry(self, func: Callable[..., Any]) -> Any:
        """带指数退避 (Exponential Backoff) 的函数执行策略。"""
        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                try:
                    return func(attempt=attempt)
                except TypeError:
                    return func()
            except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as error:
                last_exception = error
                if attempt == self.max_retries:
                    break
                print(f"⚠️ [RetryPolicy] 遇到网络波动/请求超时 ({error})，第 {attempt}/{self.max_retries} 次重试，休眠 {delay}s...")
                time.sleep(delay)
                delay *= 2.0
            except Exception as error:
                raise error

        raise ConnectionError(f"请求重试 {self.max_retries} 次后依然失败。最终错误: {last_exception}") from last_exception

    @staticmethod
    def format_tool_error_feedback(tool_name: str, error_message: str) -> str:
        """为大模型生成工具报错自省反馈 Prompt。"""
        return (
            f"❌ [工具 {tool_name} 执行报错]: {error_message}\n"
            f"请分析错误原因（例如检查路径是否存在、语法参数是否正确），调整参数或更换工具后重新尝试。"
        )
