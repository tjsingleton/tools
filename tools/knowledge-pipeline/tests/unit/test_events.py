from __future__ import annotations

from kp.events import EventStore, ItemIngested


def test_append_and_has(tmp_path):
    s = EventStore(db_path=tmp_path / "e.db")
    evt = ItemIngested(source="voice_memo", content_hash="abc", data={"k": "v"})
    rid = s.append(evt)
    assert rid > 0
    assert s.has_event(content_hash="abc", event_type="ItemIngested")
    assert not s.has_event(content_hash="xyz", event_type="ItemIngested")
    s.close()


def test_tail_filters_by_source(tmp_path):
    s = EventStore(db_path=tmp_path / "e.db")
    s.append(ItemIngested(source="voice_memo", content_hash="a"))
    s.append(ItemIngested(source="other", content_hash="b"))
    rows = list(s.tail(source="voice_memo"))
    assert len(rows) == 1
    assert rows[0]["content_hash"] == "a"
    s.close()


def test_idempotent_ingest_check(tmp_path):
    s = EventStore(db_path=tmp_path / "e.db")
    s.append(ItemIngested(source="voice_memo", content_hash="h1"))
    # simulate a second run
    assert s.has_event(content_hash="h1", event_type="ItemIngested")
    s.close()
