from __future__ import annotations

import os
from pathlib import Path

import pytest

from kp.sources.voice_memo.fingerprint import (
    FingerprintFailed,
    FingerprintUnavailable,
    cluster_by_fingerprint,
    fingerprint_file,
)

# A real .m4a from the voice memo dump for the determinism test.
_FIXTURE_M4A = Path(
    "/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP"
    "/20160821 123355-550826AF.m4a"
)


@pytest.mark.skipif(
    not _FIXTURE_M4A.exists(),
    reason="Voice memo fixture not available on this machine",
)
def test_determinism():
    """fingerprint_file on the same file twice returns identical (duration, fp)."""
    result1 = fingerprint_file(_FIXTURE_M4A)
    result2 = fingerprint_file(_FIXTURE_M4A)
    assert result1 == result2
    duration, fp = result1
    assert isinstance(duration, float)
    assert duration > 0
    assert isinstance(fp, str)
    assert len(fp) > 0


def test_missing_binary_raises_unavailable(monkeypatch, tmp_path):
    """With PATH pointing at an empty dir, fingerprint_file raises FingerprintUnavailable."""
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    monkeypatch.setenv("PATH", str(empty_bin))

    # Also need a dummy audio file path (fingerprinting won't even start)
    fake_audio = tmp_path / "test.m4a"
    fake_audio.write_bytes(b"\x00" * 16)

    with pytest.raises(FingerprintUnavailable):
        fingerprint_file(fake_audio)


def test_unreadable_file_raises_failed(tmp_path):
    """A non-audio file (or zero-byte file) raises FingerprintFailed."""
    bad = tmp_path / "not_audio.txt"
    bad.write_text("this is not audio")

    with pytest.raises((FingerprintFailed, FingerprintUnavailable)):
        fingerprint_file(bad)


def test_cluster_grouping():
    """cluster_by_fingerprint groups by fp_string using exact equality."""
    items = [
        ("h1", "fpA"),
        ("h2", "fpB"),
        ("h3", "fpA"),
    ]
    result = cluster_by_fingerprint(items)
    assert set(result["fpA"]) == {"h1", "h3"}
    assert result["fpB"] == ["h2"]


def test_cluster_single_item():
    """Single-item groups are still returned."""
    result = cluster_by_fingerprint([("h1", "fpX")])
    assert result == {"fpX": ["h1"]}


def test_cluster_empty():
    """Empty input returns empty dict."""
    assert cluster_by_fingerprint([]) == {}
