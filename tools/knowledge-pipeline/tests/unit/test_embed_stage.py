from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from kp.events import EventStore
from kp.index.sqlite_vec import VectorIndex
from kp.pipeline.plugin import Document
from kp.pipeline.stages.embed import embed_stage
from kp.providers.ollama import OllamaClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vector(seed: int, dim: int = 8) -> list[float]:
    return [float(seed + i) / 100.0 for i in range(dim)]


class _FakeOllamaClient:
    """Deterministic stub — returns a unique vector per call index."""

    model = "nomic-embed-text"

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim
        self._call_count = 0

    def embed(self, text: str, *, timeout: float = 60.0) -> list[float]:
        vec = _make_vector(self._call_count, self._dim)
        self._call_count += 1
        return vec


# ---------------------------------------------------------------------------
# embed_stage tests
# ---------------------------------------------------------------------------

def test_embed_short_text_single_chunk(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    doc = Document(content_hash="abc123", source="voice_memo", text="Short text.", metadata={})
    client = _FakeOllamaClient()

    result = embed_stage(doc, store=store, index=index, client=client)

    assert len(result) == 1
    # Verify the chunk landed in the index.
    assert index.has("abc123")
    cur = index._conn.execute(
        "SELECT chunk_index, text FROM embeddings WHERE content_hash = ?", ("abc123",)
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 0  # chunk_index
    store.close()
    index.close()


def test_embed_long_text_multiple_chunks(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    # Build a text that will definitely exceed 4000 chars so chunking kicks in.
    long_text = ("Sentence about ideas and work. " * 200)  # ~6000 chars
    doc = Document(content_hash="longhash", source="voice_memo", text=long_text, metadata={})
    client = _FakeOllamaClient()

    result = embed_stage(doc, store=store, index=index, client=client)

    # Must produce more than one embedding.
    assert len(result) > 1
    assert index.has("longhash")

    cur = index._conn.execute(
        "SELECT chunk_index FROM embeddings WHERE content_hash = ? ORDER BY chunk_index",
        ("longhash",),
    )
    rows = cur.fetchall()
    assert len(rows) == len(result)
    # Chunk indices are sequential starting at 0.
    assert [r[0] for r in rows] == list(range(len(result)))
    store.close()
    index.close()


def test_embed_skips_already_indexed(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    doc = Document(content_hash="dup", source="voice_memo", text="Some text.", metadata={})
    client = _FakeOllamaClient()

    # First call embeds.
    embed_stage(doc, store=store, index=index, client=client)
    calls_after_first = client._call_count

    # Second call should be a no-op.
    result = embed_stage(doc, store=store, index=index, client=client)
    assert result == []
    assert client._call_count == calls_after_first  # no new embed calls
    store.close()
    index.close()


def test_embed_emits_event_with_chunks_field(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    long_text = ("Detail about a decision made on Monday. " * 200)
    doc = Document(content_hash="evthash", source="voice_memo", text=long_text, metadata={})
    client = _FakeOllamaClient()

    embed_stage(doc, store=store, index=index, client=client)

    events = store.query(event_type="EmbeddingCompleted")
    assert len(events) == 1
    evt = events[0]
    assert evt["data"]["chunks"] > 1
    assert evt["data"]["model"] == "nomic-embed-text"
    assert "dim" in evt["data"]
    store.close()
    index.close()


def test_embed_empty_text_returns_empty(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    doc = Document(content_hash="empty", source="voice_memo", text="   ", metadata={})
    client = _FakeOllamaClient()

    result = embed_stage(doc, store=store, index=index, client=client)
    assert result == []
    assert not index.has("empty")
    store.close()
    index.close()


def test_embed_http_error_skips_document(tmp_path: Path, monkeypatch):
    import httpx

    store = EventStore(db_path=tmp_path / "e.db")
    index = VectorIndex(db_path=tmp_path / "idx.db")
    doc = Document(content_hash="fail1", source="voice_memo", text="Some text to embed.", metadata={})
    client = _FakeOllamaClient()

    def _raise(text, **kwargs):
        request = httpx.Request("POST", "http://localhost:11434/api/embeddings")
        raise httpx.HTTPStatusError("500 Internal Server Error", request=request, response=httpx.Response(500))

    monkeypatch.setattr(client, "embed", _raise)

    result = embed_stage(doc, store=store, index=index, client=client)
    assert result == []
    assert not index.has("fail1")
    # No event emitted for partial failure.
    events = store.query(event_type="EmbeddingCompleted")
    assert len(events) == 0
    store.close()
    index.close()


# ---------------------------------------------------------------------------
# Migration test
# ---------------------------------------------------------------------------

def test_migration_legacy_schema(tmp_path: Path):
    """VectorIndex opened against a legacy DB preserves rows at chunk_index=0."""
    db_path = tmp_path / "legacy.db"

    # Create legacy schema manually.
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE embeddings (
            content_hash TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            dim INTEGER NOT NULL
        )
        """
    )
    import json
    conn.execute(
        "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?)",
        ("hash1", "voice_memo", "Legacy text", json.dumps([0.1, 0.2]), 2),
    )
    conn.commit()
    conn.close()

    # Open VectorIndex — should auto-migrate.
    index = VectorIndex(db_path=db_path)

    assert index.has("hash1")

    cur = index._conn.execute(
        "SELECT chunk_index, text FROM embeddings WHERE content_hash = ?", ("hash1",)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == 0        # chunk_index preserved at 0
    assert row[1] == "Legacy text"

    index.close()


def test_migration_idempotent(tmp_path: Path):
    """Opening VectorIndex twice on the same DB does not corrupt data."""
    db_path = tmp_path / "idem.db"
    index1 = VectorIndex(db_path=db_path)
    index1.upsert(
        content_hash="h1", source="s", text="Hello", embedding=[0.1, 0.2]
    )
    index1.close()

    index2 = VectorIndex(db_path=db_path)
    assert index2.has("h1")
    index2.close()
