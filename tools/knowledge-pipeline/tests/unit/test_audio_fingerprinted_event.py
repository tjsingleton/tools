from __future__ import annotations

import json

from kp.events import AudioFingerprinted, EventStore


def _make_event(**kwargs) -> AudioFingerprinted:
    defaults = {
        "content_hash": "sha256abc123",
        "data": {
            "audio_fingerprint": "AQAA...",
            "audio_duration": 42.5,
            "audio_path": "/path/to/cache.m4a",
            "computed_by": "ingest",
        },
    }
    defaults.update(kwargs)
    return AudioFingerprinted(**defaults)


def test_event_construction():
    evt = _make_event()
    assert evt.event_type == "AudioFingerprinted"
    assert evt.source == "voice_memo"
    assert evt.content_hash == "sha256abc123"
    assert evt.data["audio_fingerprint"] == "AQAA..."
    assert evt.data["audio_duration"] == 42.5
    assert evt.data["audio_path"] == "/path/to/cache.m4a"
    assert evt.data["computed_by"] == "ingest"

    # round-trip through to_dict / JSON
    d = evt.to_dict()
    assert d["event_type"] == "AudioFingerprinted"
    assert d["source"] == "voice_memo"
    assert d["data"]["audio_fingerprint"] == "AQAA..."
    json_str = json.dumps(d)
    restored = json.loads(json_str)
    assert restored["data"]["audio_duration"] == 42.5


def test_event_appended_to_store(tmp_path):
    store = EventStore(db_path=tmp_path / "e.db")
    evt = _make_event()
    row_id = store.append(evt)
    assert row_id > 0
    assert store.has_event(content_hash="sha256abc123", event_type="AudioFingerprinted")

    rows = store.query(event_type="AudioFingerprinted")
    assert len(rows) == 1
    assert rows[0]["source"] == "voice_memo"
    assert rows[0]["data"]["audio_fingerprint"] == "AQAA..."
    assert rows[0]["data"]["audio_duration"] == 42.5
    assert rows[0]["data"]["computed_by"] == "ingest"
    store.close()
