from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

# Use importlib to get the actual module — the __init__.py re-exports the
# `discover` function under the same name, which shadows the module when using
# `import kp.sources.voice_memo.discover as ...` via attribute traversal.
import kp.sources.voice_memo.discover  # ensure it's in sys.modules
discover_mod = importlib.import_module("kp.sources.voice_memo.discover")

from kp.events import EventStore
from kp.pipeline.stages.ingest import ingest_stage
from kp.sources.voice_memo import VoiceMemoPlugin
from kp.sources.voice_memo.discover import discover
from kp.sources.voice_memo.fingerprint import FingerprintFailed


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_qta_m4a_pair_collapses(tmp_path: Path, monkeypatch):
    """One .qta + one .m4a with the same fingerprint → discover yields exactly one
    RawDocument, and it is the .m4a (tie-break: .m4a wins because it sorts first)."""
    m4a_data = b"shared-audio-content"
    qta_data = b"qta-blob-opaque"

    # Keep audio files in a subdirectory so the cache dir (a sibling) is not
    # picked up by rglob when we call discover(audio_dir).
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    m4a = audio_dir / "rec.m4a"
    qta = audio_dir / "rec.qta"
    m4a.write_bytes(m4a_data)
    qta.write_bytes(qta_data)

    # Pre-create a fake cache .m4a for the .qta so discover doesn't call ffmpeg.
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    qta_hash = _sha256(qta_data)
    (cache_dir / f"{qta_hash}.m4a").write_bytes(m4a_data)

    # Patch module-level names directly on the module object (avoids __init__ name
    # collision where `kp.sources.voice_memo.discover` resolves to the re-exported
    # function rather than the module).
    monkeypatch.setattr(discover_mod, "CACHE_DIR", cache_dir)

    # Both files return the same fingerprint — simulating a re-encoded duplicate.
    shared_fp = "AQAATESTFINGERPRINT"

    def mock_fingerprint(path: Path):
        return (42.0, shared_fp)

    monkeypatch.setattr(discover_mod, "fingerprint_file", mock_fingerprint)

    results = list(discover(audio_dir))

    assert len(results) == 1, f"Expected 1 RawDocument, got {len(results)}"
    assert results[0].path.suffix == ".m4a", "Expected .m4a to win the tie-break"
    assert results[0].path == m4a
    assert results[0].audio_fingerprint == (42.0, shared_fp)


def test_distinct_audio_not_collapsed(tmp_path: Path, monkeypatch):
    """Two files with different fingerprints → both RawDocuments emitted."""
    (tmp_path / "a.m4a").write_bytes(b"audio-a")
    (tmp_path / "b.m4a").write_bytes(b"audio-b")

    def mock_fingerprint(path: Path):
        return (30.0, f"FP_UNIQUE_{path.name}")

    monkeypatch.setattr(discover_mod, "fingerprint_file", mock_fingerprint)

    results = list(discover(tmp_path))

    assert len(results) == 2
    fps = {r.audio_fingerprint[1] for r in results}
    assert fps == {"FP_UNIQUE_a.m4a", "FP_UNIQUE_b.m4a"}


def test_fingerprint_failed_skips_file(tmp_path: Path, monkeypatch):
    """FingerprintFailed for one file → that file is skipped; others are emitted."""
    (tmp_path / "good.m4a").write_bytes(b"good-audio")
    (tmp_path / "bad.m4a").write_bytes(b"bad-audio")

    def mock_fingerprint(path: Path):
        if "bad" in path.name:
            raise FingerprintFailed(f"Corrupt audio: {path}")
        return (20.0, "FP_GOOD")

    monkeypatch.setattr(discover_mod, "fingerprint_file", mock_fingerprint)

    results = list(discover(tmp_path))

    assert len(results) == 1
    assert results[0].path.name == "good.m4a"


def test_ingest_emits_audio_fingerprinted(tmp_path: Path, monkeypatch):
    """End-to-end through ingest_stage: every voice_memo ItemIngested has a
    sibling AudioFingerprinted with matching content_hash."""
    (tmp_path / "a.m4a").write_bytes(b"audio-a")
    (tmp_path / "b.m4a").write_bytes(b"audio-b")

    fp_map = {
        "a.m4a": (35.0, "FP_A_AQAA"),
        "b.m4a": (40.0, "FP_B_AQAA"),
    }

    def mock_fingerprint(path: Path):
        return fp_map[path.name]

    monkeypatch.setattr(discover_mod, "fingerprint_file", mock_fingerprint)

    store = EventStore(db_path=tmp_path / "events.db")
    plugin = VoiceMemoPlugin()

    list(ingest_stage(plugin, tmp_path, store))

    ingested = store.query(event_type="ItemIngested")
    fingerprinted = store.query(event_type="AudioFingerprinted")

    assert len(ingested) == 2
    assert len(fingerprinted) == 2, (
        f"Expected 2 AudioFingerprinted events, got {len(fingerprinted)}"
    )

    ingested_hashes = {r["content_hash"] for r in ingested}
    fingerprinted_hashes = {r["content_hash"] for r in fingerprinted}
    assert ingested_hashes == fingerprinted_hashes, (
        "Every ItemIngested must have a sibling AudioFingerprinted"
    )

    for row in fingerprinted:
        assert row["source"] == "voice_memo"
        assert row["data"]["computed_by"] == "ingest"
        assert row["data"]["audio_fingerprint"]
        assert row["data"]["audio_duration"] > 0
        assert row["data"]["audio_path"]

    store.close()
