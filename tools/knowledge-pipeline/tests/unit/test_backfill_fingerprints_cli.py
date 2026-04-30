from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kp.cli import cli
from kp.events import AudioFingerprinted, EventStore, ItemIngested
from kp.sources.voice_memo.fingerprint import FingerprintFailed, FingerprintUnavailable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HASHES = [f"{chr(ord('a') + i) * 64}" for i in range(3)]  # aaa...64, bbb...64, ccc...64


def _seed_store(db_path: Path, audio_dir: Path, n: int = 3) -> list[str]:
    """Seed EventStore with n voice_memo ItemIngested events; create audio stubs."""
    store = EventStore(db_path=db_path)
    hashes = HASHES[:n]
    for i, ch in enumerate(hashes):
        audio = audio_dir / f"audio{i}.m4a"
        audio.write_bytes(b"stub")
        store.append(
            ItemIngested(
                content_hash=ch,
                source="voice_memo",
                data={"path": str(audio)},
            )
        )
    store.close()
    return hashes


def _mock_fp(path: Path) -> tuple[float, str]:
    """Deterministic fingerprint: unique per filename."""
    stem = Path(path).stem
    return (10.0, f"FP_{stem}")


def _invoke(runner: CliRunner, db_path: Path, args: list[str], monkeypatch):
    """Run the CLI with EventStore redirected to tmp db."""
    monkeypatch.setattr("kp.events.store.DEFAULT_DB_PATH", db_path)
    return runner.invoke(cli, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_no_events_written(tmp_path, monkeypatch):
    """--dry-run computes fingerprints but writes zero AudioFingerprinted events."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db = tmp_path / "events.db"
    _seed_store(db, audio_dir, n=3)

    monkeypatch.setattr("kp.sources.voice_memo.fingerprint.fingerprint_file", _mock_fp)

    runner = CliRunner()
    result = _invoke(runner, db, ["voice-memo", "backfill-fingerprints", "--dry-run"], monkeypatch)

    assert result.exit_code == 0, result.output
    out = json.loads(result.output.split("\n\n")[0])  # first JSON block
    assert out["candidates"] == 3
    assert out["emitted"] == 3
    assert out["dry_run"] is True

    # No AudioFingerprinted events should be written
    store = EventStore(db_path=db)
    assert store.query(event_type="AudioFingerprinted") == []
    store.close()


def test_real_run_emits_one_per_candidate(tmp_path, monkeypatch):
    """--no-dry-run emits exactly one AudioFingerprinted per candidate."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db = tmp_path / "events.db"
    hashes = _seed_store(db, audio_dir, n=3)

    monkeypatch.setattr("kp.sources.voice_memo.fingerprint.fingerprint_file", _mock_fp)

    runner = CliRunner()
    result = _invoke(runner, db, ["voice-memo", "backfill-fingerprints", "--no-dry-run"], monkeypatch)

    assert result.exit_code == 0, result.output
    out = json.loads(result.output.split("\n\n")[0])
    assert out["emitted"] == 3
    assert out["dry_run"] is False

    store = EventStore(db_path=db)
    fp_events = store.query(event_type="AudioFingerprinted")
    assert len(fp_events) == 3
    emitted_hashes = {e["content_hash"] for e in fp_events}
    assert emitted_hashes == set(hashes)
    for e in fp_events:
        assert e["data"]["computed_by"] == "backfill"
        assert e["data"]["audio_duration"] == 10.0
    store.close()


def test_idempotent_rerun(tmp_path, monkeypatch):
    """Running twice (--no-dry-run) emits 0 events on the second run."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db = tmp_path / "events.db"
    _seed_store(db, audio_dir, n=3)

    monkeypatch.setattr("kp.sources.voice_memo.fingerprint.fingerprint_file", _mock_fp)

    runner = CliRunner()
    args = ["voice-memo", "backfill-fingerprints", "--no-dry-run"]

    # First run
    r1 = _invoke(runner, db, args, monkeypatch)
    assert r1.exit_code == 0
    out1 = json.loads(r1.output.split("\n\n")[0])
    assert out1["emitted"] == 3

    # Second run: all already fingerprinted
    r2 = _invoke(runner, db, args, monkeypatch)
    assert r2.exit_code == 0
    out2 = json.loads(r2.output.split("\n\n")[0])
    assert out2["emitted"] == 0
    assert out2["skipped_already_fingerprinted"] == 3

    store = EventStore(db_path=db)
    assert len(store.query(event_type="AudioFingerprinted")) == 3  # still just 3
    store.close()


def test_cluster_report_groups_duplicates(tmp_path, monkeypatch):
    """Two items with the same fingerprint appear together in the cluster report."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db = tmp_path / "events.db"
    _seed_store(db, audio_dir, n=3)

    # audio0 and audio1 share the same fingerprint; audio2 is unique
    def _dup_fp(path: Path) -> tuple[float, str]:
        stem = Path(path).stem
        if stem in ("audio0", "audio1"):
            return (10.0, "FP_SHARED")
        return (10.0, "FP_UNIQUE")

    monkeypatch.setattr("kp.sources.voice_memo.fingerprint.fingerprint_file", _dup_fp)

    runner = CliRunner()
    result = _invoke(runner, db, ["voice-memo", "backfill-fingerprints", "--dry-run"], monkeypatch)

    assert result.exit_code == 0, result.output
    out = json.loads(result.output.split("\n\n")[0])
    assert out["clusters_with_duplicates"] == 1

    # Cluster section should appear in output
    assert "FP_SHARED"[:16] in result.output or "clusters" in result.output


def test_missing_binary_exits_early(tmp_path, monkeypatch):
    """FingerprintUnavailable causes a non-zero exit and zero events written."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db = tmp_path / "events.db"
    _seed_store(db, audio_dir, n=2)

    def _raise_unavailable(path: Path) -> tuple[float, str]:
        raise FingerprintUnavailable("fpcalc not found")

    monkeypatch.setattr("kp.sources.voice_memo.fingerprint.fingerprint_file", _raise_unavailable)

    runner = CliRunner()
    # Use catch_exceptions=False would re-raise; we want to inspect the click error
    monkeypatch.setattr("kp.events.store.DEFAULT_DB_PATH", db)
    result = runner.invoke(cli, ["voice-memo", "backfill-fingerprints", "--no-dry-run"])

    assert result.exit_code != 0
    assert "chromaprint" in result.output.lower() or "fpcalc" in result.output.lower()

    store = EventStore(db_path=db)
    assert store.query(event_type="AudioFingerprinted") == []
    store.close()
