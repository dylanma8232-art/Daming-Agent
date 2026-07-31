from conversation_runtime import ConversationRuntime


def test_duplicate_delivery_does_not_create_a_second_turn(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    first = runtime.accept(source="cli", delivery_id="d1", session_id="s1", content="hello")
    duplicate = runtime.accept(source="cli", delivery_id="d1", session_id="s1", content="hello")
    assert not first["duplicate"]
    assert duplicate["duplicate"]
    assert duplicate["id"] == first["id"]


def test_later_message_supersedes_the_old_turn(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    first = runtime.accept(source="cli", delivery_id="d1", session_id="s1", content="morning question")
    second = runtime.accept(source="cli", delivery_id="d2", session_id="s1", content="new question")
    assert not runtime.is_current("s1", first["epoch"])
    assert runtime.is_current("s1", second["epoch"])


def test_cancel_invalidates_current_turn(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    turn = runtime.accept(source="cli", delivery_id="d1", session_id="s1", content="work")
    runtime.cancel_session("s1")
    assert not runtime.is_current("s1", turn["epoch"])


def test_session_summary_is_durable_and_can_be_cleared(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    runtime.save_context_summary("s1", "用户要完成发布，尚待验收。", 8)
    assert runtime.get_context_summary("s1") == "用户要完成发布，尚待验收。"
    runtime.clear_context_summary("s1")
    assert runtime.get_context_summary("s1") == ""


def test_recovery_reclaims_an_unfinished_delivery(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    first = runtime.accept(source="feishu", delivery_id="m1", session_id="s1", content="work")
    recovered = runtime.recover(source="feishu", delivery_id="m1", session_id="s1", content="work")
    assert not recovered["duplicate"]
    assert recovered["id"] == first["id"]
    assert recovered["epoch"] > first["epoch"]


def test_recovery_never_replays_a_completed_delivery(tmp_path):
    runtime = ConversationRuntime(tmp_path / "conversations.sqlite3")
    first = runtime.accept(source="feishu", delivery_id="m1", session_id="s1", content="done")
    runtime.finish(first["id"], "completed")
    recovered = runtime.recover(source="feishu", delivery_id="m1", session_id="s1", content="done")
    assert recovered["duplicate"]
