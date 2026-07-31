"""渠道无关的会话边界。

任何新渠道只需构造 IncomingMessage；不得自行拼接 history、browser 或 memory 的键。
"""
from dataclasses import dataclass
import hashlib

from channels.base import IncomingMessage
from config import AppConfig


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    channel_name: str
    conversation_id: str
    user_id: str
    scope: str


class SessionManager:
    """将渠道消息映射为稳定、不可冲突且不泄露身份的会话 ID。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def resolve(self, incoming: IncomingMessage) -> SessionContext:
        channel = incoming.channel_name.strip() or "unknown"
        conversation = (incoming.conversation_id or incoming.chat_id or "default").strip()
        user_id = (incoming.user_id or "anonymous").strip()
        chat_type = (incoming.chat_type or "").lower()

        # 默认按对话隔离。群聊按群共享，以便同一群的多人能接续任务；
        # 需要群成员私有上下文时可配置为 participant。
        scope = self.config.get(f"sessions.channels.{channel}.scope", "conversation")
        if channel == "feishu" and chat_type == "group":
            scope = self.config.get("sessions.channels.feishu.group_scope", scope)
        elif channel == "feishu" and chat_type == "p2p":
            scope = self.config.get("sessions.channels.feishu.p2p_scope", scope)

        parts = ["v1", channel, conversation]
        if scope == "participant":
            parts.append(user_id)
        elif scope != "conversation":
            raise ValueError(f"不支持的会话隔离策略: {scope}")

        canonical = "\x1f".join(parts)
        # 外部 chat/user ID 不应直接成为文件名或 trace 路径。
        session_id = "s1_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
        return SessionContext(session_id, channel, conversation, user_id, scope)
