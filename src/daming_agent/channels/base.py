from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class IncomingMessage:
    """标准化传入消息模型。"""
    channel_name: str  # 渠道标识: 'cli', 'feishu', 'dingtalk', 'wechat', 'web_api'
    chat_id: str       # 会话 / 房间 / 终端 ID
    user_id: str       # 发送者 ID
    content: str       # 消息文本内容
    conversation_id: Optional[str] = None  # 调用方提供的稳定对话 ID；缺省时回退 chat_id
    chat_type: Optional[str] = None        # p2p / group / web / cli 等会话类型
    media_files: list[str] = field(default_factory=list)  # 包含的附件路径
    raw_data: Optional[dict[str, Any]] = None             # 原始回调负载数据


@dataclass
class OutgoingMessage:
    """标准化传出消息模型。"""
    content: str                                          # 回复文本 / Markdown
    media_files: list[str] = field(default_factory=list)  # 生成的文件/截图路径
    card_data: Optional[dict[str, Any]] = None            # 飞书/钉钉富文本卡片结构


class BaseChannel(ABC):
    """渠道适配器抽象基类 (Channel Adapter Standard Interface)。"""

    def __init__(self, channel_name: str) -> None:
        self.channel_name = channel_name

    @abstractmethod
    def start(self, agent_callback) -> None:
        """启动渠道监听循环或服务，接收消息时触发 agent_callback(incoming_msg)。"""
        pass

    @abstractmethod
    def send_message(self, chat_id: str, message: OutgoingMessage) -> bool:
        """将 Agent 的传出响应消息发送到对应的平台渠道。"""
        pass

    def add_reaction(self, chat_id: str, message_id: str, reaction_type: str) -> bool:
        """为特定消息添加 Emoji 表情回复 (Reaction)。默认非必须实现。"""
        return False

    def update_status(self, chat_id: str, message_id: str, status_text: str, is_finished: bool = False) -> None:
        """更新当前消息处理状态（如思考中、调用工具中等）。默认非必须实现。"""
        pass

    def push_steering_message(self, chat_id: str, text: str) -> None:
        """推送中途干预指令到此 session 的干预信号队列。"""
        if not hasattr(self, "_steering_queues"):
            self._steering_queues: dict[str, list[str]] = {}
        if chat_id and text:
            self._steering_queues.setdefault(chat_id, []).append(text)

    def pop_steering_message(self, chat_id: str) -> Optional[str]:
        """弹出此 session 当前待处理的中途干预指令。"""
        if not hasattr(self, "_steering_queues"):
            return None
        queue = self._steering_queues.get(chat_id, [])
        return queue.pop(0) if queue else None


