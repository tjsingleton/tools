from __future__ import annotations

from pathlib import Path

from kp.sources.voice_memo.discover import discover, sha256_file


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
