import os
import json
import ssl
import time
import threading
import sqlite3
from collections import deque
from typing import Any, Callable, Optional
from dotenv import load_dotenv

from logger import get_logger

logger = get_logger("feishu")

try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
except Exception:
    pass

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    CreateMessageRequest,
    CreateMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
    CreateMessageReactionRequest,
    CreateMessageReactionRequestBody,
    DeleteMessageReactionRequest,
    Emoji,
)

from channels.base import BaseChannel, IncomingMessage, OutgoingMessage



def build_feishu_card(
    markdown_text: str,
    title: Optional[str] = None,
    is_finished: bool = False,
    model_info: Optional[str] = None,
    status_text: Optional[str] = None,
) -> str:
    """构建飞书官方标准 Markdown 交互卡片 JSON 结构。

    - 自动提取正文片段写入 `config.summary.content`，确保飞书侧边栏展示实际回答文本（对比图1）。
    - 允许取消顶部冗余绿条 header（完成时自动精简 header），且支持在底部展示模型/状态元信息 Note（对标大明天子）。
    - 在思考中或执行工具时实时渲染状态。
    """
    raw_content = markdown_text.strip() if markdown_text else ""
    if not raw_content or raw_content == "\u200b":
        summary_preview = status_text or "⏳ 正在思考并处理中..."
    else:
        clean_lines = [line.lstrip("#*-> ").strip() for line in raw_content.splitlines() if line.strip()]
        summary_preview = " ".join(clean_lines)

    if len(summary_preview) > 100:
        summary_preview = summary_preview[:100] + "..."

    card_data: dict[str, Any] = {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": True,
            "summary": {
                "content": summary_preview
            }
        },
        "elements": []
    }

    # 只有当显式指定 title 时（例如思考/处理阶段），才渲染顶部 header
    if title:
        header_template = "green" if is_finished else "blue"
        card_data["header"] = {
            "title": {
                "tag": "plain_text",
                "content": title
            },
            "template": header_template
        }

    display_text = markdown_text
    if not display_text or display_text == "\u200b":
        display_text = f"⏳ **{status_text or '正在思考并处理中...'}**"
    elif status_text and not is_finished:
        display_text = f"💡 *{status_text}*\n\n{markdown_text}"

    card_data["elements"].append({
        "tag": "markdown",
        "content": display_text
    })

    if is_finished and model_info:
        card_data["elements"].extend([
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 重新生成"},
                        "type": "default",
                        "value": {"action": "replan"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 复制结论"},
                        "type": "primary",
                        "value": {"action": "copy_summary"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": model_info
                    }
                ]
            }
        ])

    return json.dumps(card_data, ensure_ascii=False)




class FeishuChannel(BaseChannel):
    """基于飞书官方 Python SDK (lark-oapi) 的长连接 Bot 渠道。"""

    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None) -> None:
        super().__init__(channel_name="feishu")
        load_dotenv()
        self.app_id = app_id or os.getenv("FEISHU_APP_ID", "")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET", "")
        if not self.app_id or not self.app_secret:
            raise ValueError("未配置飞书凭证。请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET。")

        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()

        self.agent_callback: Optional[Callable[[IncomingMessage], OutgoingMessage]] = None
        self.agent_stream_callback: Optional[Callable] = None
        self.agent_ingress_callback: Optional[Callable[[IncomingMessage], bool]] = None
        self.outbox_store = None
        # All normal deliveries for a chat are drained by one local worker.  The
        # process lock in app.py makes this the sole owner; unlike the previous
        # lease this queue never silently discards a later user message.
        self._chat_queues: dict[str, deque[tuple[int, IncomingMessage, str]]] = {}
        self._chat_generations: dict[str, int] = {}
        self._chat_workers: set[str] = set()
        self._chat_control_ready: dict[str, threading.Event] = {}
        self._chat_queue_guard = threading.RLock()
        self._message_reactions: dict[str, tuple[str, str]] = {}
        self.agent_control_callback: Optional[Callable[[IncomingMessage, str], None]] = None

        # SQLite gives all bot processes on this machine one shared, atomic view
        # of deliveries.  This is deliberately not an in-memory set: Feishu can
        # retry hours later and two accidentally started processes must agree.
        self._event_store_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "data", "feishu_event_dedupe.sqlite3"
        ))
        self._event_ttl_seconds = int(os.getenv("FEISHU_EVENT_DEDUPE_TTL_SECONDS", str(48 * 3600)))
        self._chat_lease_seconds = int(os.getenv("FEISHU_CHAT_LEASE_SECONDS", str(2 * 3600)))
        self._init_event_store()

    def _event_db(self) -> sqlite3.Connection:
        """Open a short-lived connection so sqlite locking is process-safe."""
        conn = sqlite3.connect(self._event_store_path, timeout=1.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=1000")
        return conn

    def _init_event_store(self) -> None:
        os.makedirs(os.path.dirname(self._event_store_path), exist_ok=True)
        with self._event_db() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS feishu_delivery_dedupe "
                "(delivery_key TEXT PRIMARY KEY, expires_at REAL NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS feishu_chat_runs "
                "(chat_id TEXT PRIMARY KEY, expires_at REAL NOT NULL)"
            )
            # The inbox is the source of truth for accepted user messages.  A
            # delivery must survive the interval between the WebSocket ACK and
            # a background worker actually starting.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS feishu_inbox "
                "(message_id TEXT PRIMARY KEY, event_id TEXT, chat_id TEXT NOT NULL, "
                "user_id TEXT NOT NULL, chat_type TEXT NOT NULL, content TEXT NOT NULL, "
                "status TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feishu_inbox_status_chat "
                         "ON feishu_inbox(status, chat_id, created_at)")

    def _claim_delivery(self, event_id: str, message_id: str, inbox: Optional[dict[str, str]] = None) -> bool:
        """Atomically claim an at-least-once Feishu delivery across processes."""
        keys = [f"event:{event_id}"] if event_id else []
        if message_id:
            keys.append(f"message:{message_id}")
        if not keys:
            # A message_id is present on normal im.message.receive events.  Do
            # not run an unidentifiable delivery because it cannot be idempotent.
            logger.error("❌ [飞书去重] 事件缺少 event_id 和 message_id，安全起见忽略")
            return False
        now = time.time()
        try:
            with self._event_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM feishu_delivery_dedupe WHERE expires_at <= ?", (now,))
                duplicate = any(
                    conn.execute(
                        "SELECT 1 FROM feishu_delivery_dedupe WHERE delivery_key = ?", (key,)
                    ).fetchone()
                    for key in keys
                )
                if duplicate:
                    conn.execute("COMMIT")
                    return False
                expiry = now + self._event_ttl_seconds
                conn.executemany(
                    "INSERT INTO feishu_delivery_dedupe(delivery_key, expires_at) VALUES (?, ?)",
                    [(key, expiry) for key in keys],
                )
                if inbox is not None:
                    conn.execute(
                        "INSERT INTO feishu_inbox(message_id, event_id, chat_id, user_id, chat_type, content, status, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
                        (message_id, event_id or None, inbox["chat_id"], inbox["user_id"],
                         inbox["chat_type"], inbox["content"], now, now),
                    )
                conn.execute("COMMIT")
                return True
        except sqlite3.Error as exc:
            # Failing open here recreates the incident (duplicate replies).  A
            # later Feishu retry can deliver the message after the store recovers.
            logger.error(f"❌ [飞书去重存储异常] 已抑制本次投递: {exc}")
            return False

    def start(self, agent_callback, agent_stream_callback=None, agent_control_callback=None, agent_ingress_callback=None, outbox_store=None) -> None:
        self.agent_callback = agent_callback
        self.agent_stream_callback = agent_stream_callback
        self.agent_control_callback = agent_control_callback
        self.agent_ingress_callback = agent_ingress_callback
        self.outbox_store = outbox_store
        self._resume_pending_inbox()

        def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
            # This SDK callback must return within Feishu's 3-second deadline.
            # _handle_incoming_event only validates/deduplicates then starts a
            # daemon worker; all LLM and card network work is off the callback.
            self._handle_incoming_event(data)

        event_handler = lark.EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
            .build()

        ws_client = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )

        logger.info(f"=== 飞书 WebSocket 长连接适配器启动中 (App ID: {self.app_id}) ===")
        logger.info("💡 提示：已与飞书开放平台建立 WebSocket 长连接，等待消息回调中...")
        ws_client.start()

    def _handle_incoming_event(self, data: P2ImMessageReceiveV1) -> None:
        """Fast, testable Feishu callback path; never runs the agent inline."""
        callback_started = time.monotonic()
        try:
                event = data.event
                message = event.message
                sender = event.sender
                header = getattr(data, "header", None)
                event_id = getattr(header, "event_id", "") or ""
                inbound_message_id = getattr(message, "message_id", "") or ""

                sender_type = getattr(sender, "sender_type", "unknown")
                logger.info(
                    f"📩 [收到飞书消息事件] SenderType: {sender_type} | ChatID: {message.chat_id} "
                    f"| EventID: {event_id or '-'} | MessageID: {inbound_message_id or '-'}"
                )

                # 1. 过滤：忽略来自 Bot 自己的消息，仅处理用户消息
                if sender_type != "user":
                    logger.info(f"ℹ️ [忽略非用户消息] sender_type={sender_type}")
                    return

                user_id = "unknown"
                if sender.sender_id:
                    user_id = getattr(sender.sender_id, "open_id", None) or getattr(sender.sender_id, "user_id", "unknown")

                chat_id = message.chat_id
                chat_type = getattr(message, "chat_type", "p2p")

                # 2. 解析文本消息内容
                text_content = ""
                if message.message_type == "text":
                    body = json.loads(message.content)
                    text_content = body.get("text", "").strip()
                else:
                    text_content = f"（收到非文本消息，类型: {message.message_type}）"

                # 3. 路由规则 A: 群聊必须 @机器人 才能触发
                if chat_type == "group":
                    mentions = getattr(message, "mentions", None) or []
                    if not mentions:
                        logger.info("ℹ️ [群聊消息过滤]: 群聊消息未 @ 机器人，静默忽略")
                        return
                    for m in mentions:
                        if hasattr(m, "key") and m.key:
                            text_content = text_content.replace(m.key, "").strip()

                if not text_content:
                    return

                # 4. 路由规则 B: 私聊身份配对 / 白名单鉴权
                admin_open_id = os.getenv("FEISHU_ADMIN_OPEN_ID", "").strip()
                allowed_users_env = os.getenv("FEISHU_ALLOWED_USERS", "*").strip()
                allowed_set = set()
                if admin_open_id:
                    allowed_set.add(admin_open_id)
                if allowed_users_env and allowed_users_env != "*":
                    allowed_set.update(u.strip() for u in allowed_users_env.split(",") if u.strip())

                if allowed_set and allowed_users_env != "*":
                    if user_id not in allowed_set:
                        logger.warning(f"🔒 [鉴权拦截]: 飞书用户 Open ID `{user_id}` 未在允许白名单 ({allowed_set}) 中")
                        deny_card_json = build_feishu_card(
                            markdown_text=f"🔒 **身份未配对授权**\n\n您的飞书 Open ID 为：`{user_id}`\n此 Agent 设置了私聊配对鉴权，请联系超级管理员在 `.env` 的 `FEISHU_ALLOWED_USERS` 中绑定该 ID。",
                            title="🔒 权限拦截",
                            is_finished=True
                        )
                        # Authorization feedback is intentionally dispatched in
                        # the worker too, keeping this callback under 3 seconds.
                        threading.Thread(
                            target=self.send_card_raw, args=(chat_id, deny_card_json), daemon=True,
                            name=f"feishu-deny-{chat_id[-8:]}",
                        ).start()
                        return

                logger.info(f"📩 [飞书收到消息] Type: {chat_type} | Sender: {user_id} | Content: {text_content}")

                incoming = IncomingMessage(
                    channel_name=self.channel_name,
                    chat_id=chat_id,
                    user_id=user_id,
                    content=text_content,
                    conversation_id=chat_id,
                    chat_type=chat_type,
                    raw_data={"message_id": inbound_message_id, "event_id": event_id},
                )

                # Commit a durable inbox record before returning from the SDK
                # callback.  On a crash after ACK, startup can resume this row
                # instead of silently losing the message.
                if not self._claim_delivery(event_id, inbound_message_id, {
                    "chat_id": chat_id, "user_id": user_id,
                    "chat_type": chat_type, "content": text_content,
                }):
                    logger.info(
                        f"♻️ [飞书重复投递已合并] chat_id={chat_id} "
                        f"event_id={event_id or '-'} message_id={inbound_message_id or '-'}"
                    )
                    return

                # 收到合法用户消息后，立刻给用户发的消息添加 👀 表情回复
                if inbound_message_id:
                    threading.Thread(
                        target=self.add_reaction,
                        args=(chat_id, inbound_message_id, "EYES"),
                        daemon=True,
                        name=f"feishu-eyes-{inbound_message_id[-6:]}",
                    ).start()

                command = self._control_action(text_content)

                if command == "stop":
                    self._schedule_chat_control(chat_id, incoming, "stop")
                elif command == "new":
                    self._schedule_chat_control(chat_id, incoming, "new")
                else:
                    if self.agent_ingress_callback and not self.agent_ingress_callback(incoming):
                        logger.info(f"♻️ [Agent Ingress 重复消息已抑制] chat_id={chat_id}")
                        return
                    self._enqueue_chat_message(chat_id, incoming, inbound_message_id)

        except Exception as e:
            logger.error(f"❌ [飞书处理消息失败]: {e}", exc_info=True)
        finally:
            logger.info(f"⏱️ [飞书事件回调已确认] elapsed={time.monotonic() - callback_started:.3f}s")

    @staticmethod
    def _control_action(text: str) -> Optional[str]:
        """Recognize only unambiguous, short conversation control requests.

        Users commonly write natural variants such as ``暂停 停止吧`` rather
        than a literal slash command.  Do not treat a status question (for
        example ``停止了吗``) as an instruction to cancel work.
        """
        command = " ".join(text.strip().lower().split())
        if command in {"/new", "新对话", "开始新对话"}:
            return "new"
        if command == "/stop":
            return "stop"
        if len(command) <= 60 and ("停止" in command or "暂停" in command):
            if not any(marker in command for marker in ("停止了吗", "暂停了吗", "是否停止", "有没有停止")):
                return "stop"
        return None

    def _enqueue_chat_message(self, chat_id: str, incoming: IncomingMessage, inbound_message_id: str) -> None:
        """Append a delivery and ensure exactly one FIFO worker drains this chat."""
        with self._chat_queue_guard:
            generation = self._chat_generations.setdefault(chat_id, 0)
            ready = self._chat_control_ready.setdefault(chat_id, threading.Event())
            ready.set()
            queue = self._chat_queues.setdefault(chat_id, deque())
            queue.append((generation, incoming, inbound_message_id))
            queue_depth = len(queue)
            if chat_id in self._chat_workers:
                logger.info(f"📬 [飞书消息已排队] chat_id={chat_id} depth={queue_depth}")
                return
            self._chat_workers.add(chat_id)
        threading.Thread(
            target=self._drain_chat_queue, args=(chat_id,), daemon=True,
            name=f"feishu-agent-{chat_id[-8:]}",
        ).start()

    def _resume_pending_inbox(self) -> None:
        """Recover accepted work after a clean restart or a process crash."""
        try:
            with self._event_db() as conn:
                # A previous process cannot safely continue an in-flight model
                # request. Requeue it; the durable delivery key prevents a new
                # Feishu retry from creating another business task.
                conn.execute("UPDATE feishu_inbox SET status='queued', updated_at=? WHERE status='processing'", (time.time(),))
                rows = conn.execute(
                    "SELECT message_id, chat_id, user_id, chat_type, content FROM feishu_inbox "
                    "WHERE status='queued' ORDER BY created_at ASC"
                ).fetchall()
            for message_id, chat_id, user_id, chat_type, content in rows:
                incoming = IncomingMessage(
                    channel_name=self.channel_name, chat_id=chat_id, user_id=user_id,
                    content=content, conversation_id=chat_id, chat_type=chat_type,
                    raw_data={"recovered": True, "message_id": message_id},
                )
                self._enqueue_chat_message(chat_id, incoming, message_id)
            if rows:
                logger.info(f"♻️ [飞书 Inbox 恢复] queued={len(rows)}")
        except sqlite3.Error as exc:
            logger.error(f"❌ [飞书 Inbox 恢复失败]: {exc}")

    def _set_inbox_status(self, message_id: str, status: str) -> None:
        if not message_id:
            return
        try:
            with self._event_db() as conn:
                conn.execute("UPDATE feishu_inbox SET status=?, updated_at=? WHERE message_id=?", (status, time.time(), message_id))
        except sqlite3.Error as exc:
            logger.warning(f"⚠️ [飞书 Inbox 状态更新失败] message_id={message_id}: {exc}")

    def _drain_chat_queue(self, chat_id: str) -> None:
        while True:
            with self._chat_queue_guard:
                queue = self._chat_queues.get(chat_id)
                if not queue:
                    self._chat_workers.discard(chat_id)
                    return
                generation, incoming, inbound_message_id = queue.popleft()
                control_ready = self._chat_control_ready.setdefault(chat_id, threading.Event())
                # A control command invalidates pending work before it is run.
                if generation != self._chat_generations.get(chat_id, 0):
                    continue
                setattr(incoming, "_feishu_generation", generation)
                self._set_inbox_status(inbound_message_id, "processing")
            # Complete a deterministic /new or /stop before a later queued
            # message is allowed to observe this conversation.
            control_ready.wait()
            with self._chat_queue_guard:
                if generation != self._chat_generations.get(chat_id, 0):
                    continue
            started = time.monotonic()
            try:
                self._handle_card_stream_reply(chat_id, incoming)
                logger.info(
                    f"✅ [飞书后台处理完成] chat_id={chat_id} "
                    f"message_id={inbound_message_id or '-'} elapsed={time.monotonic() - started:.2f}s"
                )
            except Exception as exc:
                logger.error(f"❌ [飞书后台处理失败] chat_id={chat_id}: {exc}", exc_info=True)
                self._set_inbox_status(inbound_message_id, "failed")
            else:
                self._set_inbox_status(inbound_message_id, "completed")

    def _schedule_chat_control(self, chat_id: str, incoming: IncomingMessage, action: str) -> None:
        """Invalidate old output immediately; control work itself stays off the SDK callback."""
        with self._chat_queue_guard:
            self._chat_generations[chat_id] = self._chat_generations.get(chat_id, 0) + 1
            cleared = len(self._chat_queues.setdefault(chat_id, deque()))
            self._chat_queues[chat_id].clear()
            control_ready = threading.Event()
            self._chat_control_ready[chat_id] = control_ready
        threading.Thread(
            target=self._run_chat_control, args=(chat_id, incoming, action, cleared, control_ready), daemon=True,
            name=f"feishu-control-{chat_id[-8:]}",
        ).start()

    def _run_chat_control(self, chat_id: str, incoming: IncomingMessage, action: str, cleared: int, control_ready: threading.Event) -> None:
        try:
            if self.agent_control_callback:
                self.agent_control_callback(incoming, action)
            text = (
                "已停止当前任务，并清空待处理消息。"
                if action == "stop"
                else "已开始新对话；之前任务的结果不会再发送。"
            )
            logger.info(f"🛑 [飞书会话控制] action={action} chat_id={chat_id} cleared={cleared}")
            self.send_card_raw(chat_id, build_feishu_card(text, title="🤖 Daming Agent", is_finished=True))
        except Exception as exc:
            logger.error(f"❌ [飞书会话控制失败] action={action} chat_id={chat_id}: {exc}", exc_info=True)
        finally:
            with self._chat_queue_guard:
                if self._chat_control_ready.get(chat_id) is control_ready:
                    control_ready.set()

    def _is_current_generation(self, chat_id: str, incoming: IncomingMessage) -> bool:
        generation = getattr(incoming, "_feishu_generation", None)
        with self._chat_queue_guard:
            return generation is None or generation == self._chat_generations.get(chat_id, 0)

    def _handle_card_stream_reply(self, chat_id: str, incoming: IncomingMessage) -> None:
        """使用飞书官方交互卡片并在生成过程中实施卡片流式打字机 Patch 更新。"""
        if not self._is_current_generation(chat_id, incoming):
            return

        inbound_message_id = (incoming.raw_data or {}).get("message_id", "")

        # 先创建带“思考中...”状态的可流式更新卡片
        initial_card_json = build_feishu_card("", title="⏳ 思考中...", is_finished=False, status_text="正在思考并处理中...")
        message_id = self.send_card_raw(chat_id, initial_card_json)

        if not message_id:
            if self.agent_callback:
                outgoing = self.agent_callback(incoming)
                if self._is_current_generation(chat_id, incoming):
                    self.send_message(chat_id, outgoing)
                else:
                    logger.info(f"🚫 [飞书已抑制过期降级结果] chat_id={chat_id}")
            return

        accumulated_text = ""
        last_update_time = [time.time()]
        current_status = ["正在思考并处理中..."]

        def stream_chunk_handler(chunk: str):
            nonlocal accumulated_text
            if not self._is_current_generation(chat_id, incoming):
                return
            accumulated_text += chunk
            now = time.time()
            if now - last_update_time[0] >= 0.3:
                last_update_time[0] = now
                card_json = build_feishu_card(accumulated_text, title="✍️ 回复中...", is_finished=False, status_text=current_status[0])
                self.patch_card_raw(message_id, card_json)

        def status_update_handler(status_text: str):
            nonlocal accumulated_text
            if not self._is_current_generation(chat_id, incoming):
                return
            current_status[0] = status_text
            card_json = build_feishu_card(accumulated_text, title="⏳ 处理中...", is_finished=False, status_text=status_text)
            self.patch_card_raw(message_id, card_json)

        if self.agent_stream_callback:
            try:
                sig = inspect.signature(self.agent_stream_callback)
                accepts_status = "on_status" in sig.parameters
            except Exception:
                accepts_status = False

            if accepts_status:
                outgoing = self.agent_stream_callback(incoming, on_chunk=stream_chunk_handler, on_status=status_update_handler)
            else:
                outgoing = self.agent_stream_callback(incoming, on_chunk=stream_chunk_handler)

            if outgoing and outgoing.card_data and outgoing.card_data.get("suppressed"):
                logger.info(f"🚫 [Agent Runtime 已抑制过期结果] chat_id={chat_id}")
                return
            final_text = outgoing.content if outgoing and outgoing.content else accumulated_text
        elif self.agent_callback:
            outgoing = self.agent_callback(incoming)
            final_text = outgoing.content
        else:
            final_text = "Agent 尚未准备就绪。"

        if self._is_current_generation(chat_id, incoming):
            final_card_json = build_feishu_card(
                final_text,
                title=None,  # 成功完成后精简顶部 banner
                is_finished=True,
                model_info="Agent: agent | Model: auto"
            )

            if self.outbox_store is None:
                self.patch_card_raw(message_id, final_card_json)
            else:
                session_id = getattr(incoming, "_agent_session_id", chat_id)
                turn = getattr(incoming, "_agent_turn", {})
                epoch = int(turn.get("epoch", 0)) if isinstance(turn, dict) else 0
                record = self.outbox_store.enqueue(
                    delivery_key=f"feishu:{chat_id}:{epoch}:final", session_id=session_id, epoch=epoch,
                    channel="feishu", target=chat_id,
                    payload={"kind": "card_patch", "message_id": message_id, "card_json": final_card_json},
                )
                self._flush_outbox()

            # 处理完成后尝试自动为用户原消息标记 ✅ 完成表情
            if inbound_message_id:
                threading.Thread(
                    target=self.add_reaction,
                    args=(chat_id, inbound_message_id, "CHECK_MARK"),
                    daemon=True,
                    name=f"feishu-done-{inbound_message_id[-6:]}",
                ).start()
        else:
            logger.info(f"🚫 [飞书已抑制过期结果] chat_id={chat_id}")


    def _flush_outbox(self) -> None:
        """Deliver durable Agent Outbox entries through this channel adapter."""
        if self.outbox_store is None:
            return
        for record in self.outbox_store.claim_due("feishu"):
            payload = record["payload"]
            try:
                ok = payload.get("kind") == "card_patch" and self.patch_card_raw(payload["message_id"], payload["card_json"])
                if ok:
                    self.outbox_store.mark_sent(record["id"], payload.get("message_id"))
                else:
                    self.outbox_store.retry(record["id"], "飞书卡片更新失败", record["attempts"])
            except Exception as exc:
                self.outbox_store.retry(record["id"], str(exc), record["attempts"])

    def send_card_raw(self, chat_id: str, card_json_str: str) -> Optional[str]:
        """发送交互卡片消息，成功则返回生成消息的 message_id。"""
        try:
            receive_id_type = "open_id" if chat_id.startswith("ou_") else "chat_id"
            req_body = CreateMessageRequestBody.builder() \
                .receive_id(chat_id) \
                .msg_type("interactive") \
                .content(card_json_str) \
                .build()

            req = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(req_body) \
                .build()

            resp = self.client.im.v1.message.create(req)
            if not resp.success():
                logger.error(f"❌ [发送飞书卡片失败]: code={resp.code}, msg={resp.msg}")
                return None

            msg_id = resp.data.message_id
            logger.info(f"📡 [已发往飞书交互卡片 ({receive_id_type}): {chat_id}] Message ID: {msg_id}")
            return msg_id
        except Exception as e:
            logger.error(f"❌ [发送飞书卡片异常]: {e}", exc_info=True)
            return None

    def patch_card_raw(self, message_id: str, card_json_str: str) -> bool:
        """通过 Patch API 实时更新已有的卡片内容。"""
        try:
            req_body = PatchMessageRequestBody.builder() \
                .content(card_json_str) \
                .build()

            req = PatchMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(req_body) \
                .build()

            resp = self.client.im.v1.message.patch(req)
            return resp.success()
        except Exception as e:
            return False

    def send_message(self, chat_id: str, message: OutgoingMessage) -> bool:
        card_json = build_feishu_card(message.content, is_finished=True, model_info="Agent: daming | Model: auto")
        return bool(self.send_card_raw(chat_id, card_json))

    def remove_reaction(self, chat_id: str, message_id: str, reaction_id: str) -> bool:
        """移除飞书消息上已有的指定 Reaction 表情。"""
        if not message_id or not reaction_id or not hasattr(self, "client"):
            return False

        try:
            if not hasattr(lark, "api") or not hasattr(lark.api.im.v1, "DeleteMessageReactionRequest"):
                return False
            req = DeleteMessageReactionRequest.builder() \
                .message_id(message_id) \
                .reaction_id(reaction_id) \
                .build()

            resp = self.client.im.v1.message_reaction.delete(req)
            return bool(resp and hasattr(resp, "success") and resp.success())
        except Exception as e:
            logger.warning(f"⚠️ [飞书 Reaction 删除异常]: {e}")
            return False

    def add_reaction(self, chat_id: str, message_id: str, reaction_type: str) -> bool:
        """为飞书消息设置独占 Emoji 表情回复 (Reaction)。

        - 自动清理该消息上之前添加过的旧表情，确保一条消息上同时只有 1 个最新状态表情（防止堆叠）。
        - 支持常用标识映射：
          - 'EYES' / 'eyes' / '👀' -> EYES (接单中)
          - 'THINKING' / 'thinking' / '🧠' -> THINKING (处理中)
          - 'CHECK_MARK' / 'check' / 'done' / '✅' -> CHECK_MARK (完成)
          - 'CROSS_MARK' / 'cross' / 'fail' / '❌' -> CROSS_MARK (失败/异常)
        """
        if not message_id or not hasattr(self, "client"):
            return False

        emoji_mapping = {
            "👀": "EYES", "eyes": "EYES", "EYES": "EYES",
            "🧠": "THINKING", "thinking": "THINKING", "THINKING": "THINKING",
            "✅": "CHECK_MARK", "check": "CHECK_MARK", "done": "CHECK_MARK", "CHECK_MARK": "CHECK_MARK", "OK": "CHECK_MARK",
            "❌": "CROSS_MARK", "cross": "CROSS_MARK", "fail": "CROSS_MARK", "CROSS_MARK": "CROSS_MARK",
        }
        target_emoji = emoji_mapping.get(reaction_type, reaction_type.upper())

        # 如果该消息之前在本地记录过已加表情，先清理旧表情
        with getattr(self, "_chat_queue_guard", threading.RLock()):
            prev = getattr(self, "_message_reactions", {}).get(message_id)

        if prev:
            prev_type, prev_reaction_id = prev
            if prev_type != target_emoji and prev_reaction_id:
                self.remove_reaction(chat_id, message_id, prev_reaction_id)

        try:
            if not hasattr(lark, "api") or not hasattr(lark.api.im.v1, "CreateMessageReactionRequest"):
                return False
            req_body = CreateMessageReactionRequestBody.builder() \
                .reaction_type(Emoji.builder().emoji_type(target_emoji).build()) \
                .build()
            req = CreateMessageReactionRequest.builder() \
                .message_id(message_id) \
                .request_body(req_body) \
                .build()

            resp = self.client.im.v1.message_reaction.create(req)
            if resp and hasattr(resp, "success") and resp.success():
                reaction_id = getattr(getattr(resp, "data", None), "reaction_id", "") or ""
                with getattr(self, "_chat_queue_guard", threading.RLock()):
                    if not hasattr(self, "_message_reactions"):
                        self._message_reactions = {}
                    self._message_reactions[message_id] = (target_emoji, reaction_id)
                logger.info(f"👍 [飞书 Reaction 状态表情已更新] message_id={message_id} emoji={target_emoji}")
                return True
            else:
                msg = getattr(resp, "msg", "") if resp else ""
                code = getattr(resp, "code", "") if resp else ""
                logger.warning(f"⚠️ [飞书 Reaction 添加失败]: code={code}, msg={msg}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ [飞书 Reaction 异常]: {e}")
            return False


