from outbox import OutboxStore


def test_outbox_claim_retry_and_send(tmp_path):
    store = OutboxStore(tmp_path / "outbox.sqlite3")
    message = store.enqueue(
        delivery_key="feishu:s1:1:final", session_id="s1", epoch=1,
        channel="feishu", target="chat", payload={"kind": "card_patch"},
    )
    claimed = store.claim_due("feishu")
    assert claimed[0]["id"] == message["id"]
    store.retry(message["id"], "temporary", attempts=1)
    # Requeue immediately for deterministic test coverage.
    with store._db() as db:
        db.execute("UPDATE outbox_messages SET next_attempt_at=0 WHERE id=?", (message["id"],))
    claimed = store.claim_due("feishu")
    store.mark_sent(claimed[0]["id"], "external-card")
    assert store.claim_due("feishu") == []


def test_newer_epoch_cancels_stale_outbox_messages(tmp_path):
    store = OutboxStore(tmp_path / "outbox.sqlite3")
    store.enqueue(delivery_key="d1", session_id="s1", epoch=1, channel="feishu", target="chat", payload={})
    store.enqueue(delivery_key="d2", session_id="s1", epoch=2, channel="feishu", target="chat", payload={})
    assert store.cancel_session_before_epoch("s1", 2) == 1
    assert [row["delivery_key"] for row in store.claim_due("feishu")] == ["d2"]
