from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from kp.sources.voice_memo.discover import discover, sha256_file

_discover_mod = importlib.import_module("kp.sources.voice_memo.discover")


@pytest.fixture(autouse=True)
def _mock_fingerprint(monkeypatch):
    """Patch fingerprint_file and _convert_qta_to_m4a for unit tests that use
    fake audio bytes — no real fpcalc or ffmpeg required."""
    call_count = [0]

    def fake_fingerprint(path: Path):
        call_count[0] += 1
        return (10.0, f"FP_{path.name}_{call_count[0]}")

    def fake_convert(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    monkeypatch.setattr(_discover_mod, "fingerprint_file", fake_fingerprint)
    monkeypatch.setattr(_discover_mod, "_convert_qta_to_m4a", fake_convert)


def test_sha256_file_deterministic(tmp_path: Path):
    p = tmp_path / "a.m4a"
    p.write_bytes(b"hello")
    h1 = sha256_file(p)
    h2 = sha256_file(p)
    assert h1 == h2
    assert len(h1) == 64


def test_discover_finds_audio_files(tmp_path: Path):
    (tmp_path / "a.m4a").write_bytes(b"data-a")
    (tmp_path / "b.qta").write_bytes(b"data-b")
    (tmp_path / "ignored.txt").write_text("nope")
    results = list(discover(tmp_path))
    assert len(results) == 2
    exts = {r.metadata["ext"] for r in results}
    assert exts == {".m4a", ".qta"}
    for r in results:
        assert len(r.content_hash) == 64
        assert r.source == "voice_memo"


def test_discover_dedupes_by_hash(tmp_path: Path):
    (tmp_path / "a.m4a").write_bytes(b"same")
    (tmp_path / "b.m4a").write_bytes(b"same")
    results = list(discover(tmp_path))
    assert len(results) == 1
