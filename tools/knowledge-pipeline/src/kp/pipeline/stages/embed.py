from __future__ import annotations

from kp.events import EmbeddingCompleted, EventStore
from kp.index.sqlite_vec import VectorIndex
from kp.pipeline.plugin import Document
from kp.providers.ollama import OllamaClient


def embed_stage(
    doc: Document,
    *,
    store: EventStore,
    index: VectorIndex,
    client: OllamaClient | None = None,
) -> list[float]:
    if not doc.text.strip():
        return []
    if index.has(doc.content_hash):
        return []
    client = client or OllamaClient()
    embedding = client.embed(doc.text)
    index.upsert(
        content_hash=doc.content_hash,
        source=doc.source,
        text=doc.text,
        embedding=embedding,
    )
    store.append(
        EmbeddingCompleted(
            source=doc.source,
            content_hash=doc.content_hash,
            data={"dim": len(embedding), "model": client.model},
        )
    )
    return embedding
