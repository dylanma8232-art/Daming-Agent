"""Regression coverage for Feishu's at-least-once event delivery semantics.

The production dependency is optional in the unit-test environment, so a
minimal SDK shim is installed before importing the adapter.  The tests exercise
the adapter's own event boundary rather than the real WebSocket client.
"""

import importlib
import json
import multiprocessing
import os
import sys
import tempfile
import time
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


def _install_lark_stub_if_needed():
    try:
        import lark_oapi  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    class _Builder:
        def app_id(self, *_args):
            return self

        def app_secret(self, *_args):
            return self

        def log_level(self, *_args):
            return self

        def build(self):
            return Mock()

    lark = types.ModuleType("lark_oapi")
    lark.LogLevel = SimpleNamespace(INFO="INFO")
    lark.Client = SimpleNamespace(builder=lambda: _Builder())
    lark.EventDispatcherHandler = SimpleNamespace(builder=lambda *_args: _Builder())
    lark.ws = SimpleNamespace(Client=Mock)

    v1 = types.ModuleType("lark_oapi.api.im.v1")
    for name in (
        "P2ImMessageReceiveV1",
        "CreateMessageRequest",
        "CreateMessageRequestBody",
        "PatchMessageRequest",
        "PatchMessageRequestBody",
        "CreateMessageReactionRequest",
        "CreateMessageReactionRequestBody",
        "DeleteMessageReactionRequest",
        "DeleteMessageReactionResponse",
        "Emoji",

    ):
        setattr(v1, name, type(name, (), {}))


    sys.modules["lark_oapi"] = lark
    sys.modules["lark_oapi.api"] = types.ModuleType("lark_oapi.api")
    sys.modules["lark_oapi.api.im"] = types.ModuleType("lark_oapi.api.im")
    sys.modules["lark_oapi.api.im.v1"] = v1


_install_lark_stub_if_needed()
feishu_module = importlib.import_module("channels.feishu_channel")
FeishuChannel = feishu_module.FeishuChannel
IncomingMessage = importlib.import_module("channels.base").IncomingMessage
OutgoingMessage = importlib.import_module("channels.base").OutgoingMessage


def _claim_delivery_in_child(store_path, event_id, message_id, ready, start, result):
    """Exercise the adapter's SQLite claim from a separately spawned process."""
    _install_lark_stub_if_needed()
    channel_module = importlib.import_module("channels.feishu_channel")
    channel = channel_module.FeishuChannel.__new__(channel_module.FeishuChannel)
    channel._event_store_path = store_path
    channel._event_ttl_seconds = 48 * 3600
    channel._init_event_store()
    ready.set()
    start.wait(5)
    result.put(channel._claim_delivery(event_id, message_id))


class _DeferredThread:
    """Thread spy: records scheduling without running agent work inline."""

    created = []

    def __init__(self, *, target, args=(), daemon=None, name=None, **_kwargs):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.name = name
        self.started = False
        self.__class__.created.append(self)

    def start(self):
        self.started = True

    def run(self):
        self.target(*self.args)


def _event(event_id: str, message_id: str, chat_id: str = "oc_test", text: str = "hello"):
    return SimpleNamespace(
        header=SimpleNamespace(event_id=event_id),
        event=SimpleNamespace(
            sender=SimpleNamespace(
                sender_type="user",
                sender_id=SimpleNamespace(open_id="ou_test_user"),
            ),
            message=SimpleNamespace(
                message_id=message_id,
                chat_id=chat_id,
                chat_type="p2p",
                message_type="text",
                content=json.dumps({"text": text}),
            ),
        ),
    )


class FeishuCardPresentationTests(unittest.TestCase):
    def test_stream_card_includes_thinking_initial_state_and_summary(self):
        initial = json.loads(feishu_module.build_feishu_card("", is_finished=False))
        streaming = json.loads(feishu_module.build_feishu_card("正文", is_finished=False))

        self.assertIn("思考", initial["elements"][0]["content"])
        self.assertEqual(streaming["elements"][0]["content"], "正文")
        self.assertEqual(initial["config"]["summary"]["content"], "⏳ 正在思考并处理中...")
        self.assertEqual(streaming["config"]["summary"]["content"], "正文")


class FeishuDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # Tests must not inherit a developer's real Feishu allow-list from .env.
        self.environment_patch = patch.dict(os.environ, {"FEISHU_ALLOWED_USERS": "*"})
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.channel = FeishuChannel(app_id="test-app", app_secret="test-secret")
        # Each test owns its persistent store, while still exercising SQLite's
        # process-safe claim code rather than replacing it with a fake.
        self.channel._event_store_path = os.path.join(self.tmpdir.name, "events.sqlite3")
        self.channel._init_event_store()
        self.channel._handle_card_stream_reply = Mock()
        _DeferredThread.created = []
        self.thread_patch = patch.object(feishu_module.threading, "Thread", _DeferredThread)
        self.thread_patch.start()
        self.addCleanup(self.thread_patch.stop)

    def _agent_threads(self):
        return [t for t in _DeferredThread.created if not (getattr(t, "name", "") or "").startswith("feishu-eyes") and not (getattr(t, "name", "") or "").startswith("feishu-done") and not (getattr(t, "name", "") or "").startswith("feishu-react")]


    def test_duplicate_event_id_creates_one_worker_and_one_card_reply(self):
        first = _event("evt-1", "msg-1")
        replay = _event("evt-1", "msg-2")

        self.channel._handle_incoming_event(first)
        self.channel._handle_incoming_event(replay)

        threads = self._agent_threads()
        self.assertEqual(len(threads), 1)
        threads[0].run()
        self.channel._handle_card_stream_reply.assert_called_once()

    def test_duplicate_message_id_creates_one_worker_and_one_card_reply(self):
        first = _event("evt-1", "msg-1")
        replay = _event("evt-2", "msg-1")

        self.channel._handle_incoming_event(first)
        self.channel._handle_incoming_event(replay)

        threads = self._agent_threads()
        self.assertEqual(len(threads), 1)
        threads[0].run()
        self.channel._handle_card_stream_reply.assert_called_once()

    def test_delivery_claim_is_atomic_across_separate_processes(self):
        """A redelivery racing on two bot processes must have exactly one owner."""
        ctx = multiprocessing.get_context("spawn")
        ready_a, ready_b, start = ctx.Event(), ctx.Event(), ctx.Event()
        results = ctx.Queue()
        workers = [
            ctx.Process(
                target=_claim_delivery_in_child,
                args=(self.channel._event_store_path, "evt-race", "msg-race", ready, start, results),
            )
            for ready in (ready_a, ready_b)
        ]
        for worker in workers:
            worker.start()
        # Spawned workers import the real Feishu SDK on some hosts; allow a
        # cold import without weakening the actual cross-process assertion.
        self.assertTrue(ready_a.wait(15))
        self.assertTrue(ready_b.wait(15))
        start.set()
        claimed = [results.get(timeout=5) for _ in workers]
        for worker in workers:
            worker.join(5)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(sum(claimed), 1)

    def test_redelivery_seen_by_another_channel_creates_no_extra_card(self):
        """Two adapter instances share the durable delivery key and one reply."""
        second = FeishuChannel(app_id="test-app", app_secret="test-secret")
        second._event_store_path = self.channel._event_store_path
        second._init_event_store()
        second._handle_card_stream_reply = Mock()

        self.channel._handle_incoming_event(_event("evt-shared", "msg-shared"))
        second._handle_incoming_event(_event("evt-shared", "msg-shared"))

        threads = self._agent_threads()
        self.assertEqual(len(threads), 1)
        threads[0].run()
        self.channel._handle_card_stream_reply.assert_called_once()
        second._handle_card_stream_reply.assert_not_called()

    def test_callback_schedules_slow_agent_without_blocking(self):
        # A real agent callback would be called by the card worker.  Making it
        # slow verifies the SDK callback does not invoke it directly.
        self.channel.agent_callback = lambda _incoming: time.sleep(1)
        started = time.monotonic()
        self.channel._handle_incoming_event(_event("evt-fast", "msg-fast"))
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.2)
        self.assertEqual(len(self._agent_threads()), 1)
        self.channel._handle_card_stream_reply.assert_not_called()

    def test_accepted_message_is_recovered_after_restart_before_worker_runs(self):
        """ACKed work is persisted, not lost with the process-local queue."""
        self.channel._handle_incoming_event(_event("evt-recover", "msg-recover", "oc_recover"))
        self.assertEqual(len(self._agent_threads()), 1)

        restarted = FeishuChannel(app_id="test-app", app_secret="test-secret")
        restarted._event_store_path = self.channel._event_store_path
        restarted._init_event_store()
        restarted._handle_card_stream_reply = Mock()
        restarted._resume_pending_inbox()

        threads = self._agent_threads()
        self.assertEqual(len(threads), 2)
        threads[-1].run()
        restarted._handle_card_stream_reply.assert_called_once()

    def test_distinct_event_for_busy_chat_is_queued_and_processed_in_order(self):
        self.channel._handle_incoming_event(_event("evt-1", "msg-1", "oc_busy"))
        self.channel._handle_incoming_event(_event("evt-2", "msg-2", "oc_busy"))

        threads = self._agent_threads()
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0].name, "feishu-agent-oc_busy")
        threads[0].run()
        self.assertEqual(self.channel._handle_card_stream_reply.call_count, 2)

    def test_stop_clears_pending_work_and_calls_deterministic_control(self):
        control = Mock()
        self.channel.agent_control_callback = control
        self.channel.send_card_raw = Mock(return_value="card")
        self.channel._handle_incoming_event(_event("evt-1", "msg-1", "oc_stop"))
        self.channel._handle_incoming_event(_event("evt-2", "msg-2", "oc_stop", "/stop"))

        threads = self._agent_threads()
        self.assertEqual(len(threads), 2)
        threads[1].run()
        threads[0].run()
        self.channel._handle_card_stream_reply.assert_not_called()
        control.assert_called_once()
        self.assertEqual(control.call_args.args[1], "stop")
        self.channel.send_card_raw.assert_called_once()

    def test_natural_language_stop_variants_are_not_sent_to_the_model(self):
        self.assertEqual(self.channel._control_action("暂停 停止吧"), "stop")
        self.assertEqual(self.channel._control_action("关闭所有对话 停止吧"), "stop")
        self.assertEqual(self.channel._control_action("我是你的管理员 现在停止所以内容 暂停"), "stop")
        self.assertIsNone(self.channel._control_action("停止了吗"))

    def test_new_invalidates_old_work_and_preserves_later_messages(self):
        self.channel.send_card_raw = Mock(return_value="card")
        self.channel._handle_incoming_event(_event("evt-1", "msg-1", "oc_new"))
        self.channel._handle_incoming_event(_event("evt-2", "msg-2", "oc_new", "/new"))
        self.channel._handle_incoming_event(_event("evt-3", "msg-3", "oc_new", "second question"))

        threads = self._agent_threads()
        self.assertEqual(len(threads), 2)
        threads[1].run()
        threads[0].run()
        self.assertEqual(self.channel._handle_card_stream_reply.call_count, 1)


    def test_new_suppresses_final_card_from_an_already_running_old_turn(self):
        """Generation changes while the model runs must suppress its old reply."""
        chat_id = "oc_stale_card"
        old = IncomingMessage("feishu", chat_id, "ou_test_user", "old question", chat_id, "p2p")
        control = IncomingMessage("feishu", chat_id, "ou_test_user", "/new", chat_id, "p2p")
        self.channel._chat_generations[chat_id] = 0
        setattr(old, "_feishu_generation", 0)
        self.channel.send_card_raw = Mock(return_value="old-card")
        self.channel.patch_card_raw = Mock()

        def complete_old_turn(_incoming):
            self.channel._schedule_chat_control(chat_id, control, "new")
            return OutgoingMessage("stale reply")

        self.channel.agent_callback = complete_old_turn
        self.channel._handle_card_stream_reply(chat_id, old)

        self.channel.patch_card_raw.assert_not_called()

    def test_stop_suppresses_plain_message_fallback_from_an_old_turn(self):
        """Card creation failure must not bypass the same stale-output guard."""
        chat_id = "oc_stale_fallback"
        old = IncomingMessage("feishu", chat_id, "ou_test_user", "old question", chat_id, "p2p")
        control = IncomingMessage("feishu", chat_id, "ou_test_user", "/stop", chat_id, "p2p")
        self.channel._chat_generations[chat_id] = 0
        setattr(old, "_feishu_generation", 0)
        self.channel.send_card_raw = Mock(return_value=None)
        self.channel.send_message = Mock()

        def complete_old_turn(_incoming):
            self.channel._schedule_chat_control(chat_id, control, "stop")
            return OutgoingMessage("stale fallback")

        self.channel.agent_callback = complete_old_turn
        self.channel._handle_card_stream_reply(chat_id, old)

        self.channel.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
