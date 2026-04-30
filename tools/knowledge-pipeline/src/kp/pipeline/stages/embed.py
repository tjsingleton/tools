from __future__ import annotations

import httpx

from kp.events import EmbeddingCompleted, EventStore
from kp.index.sqlite_vec import VectorIndex
from kp.pipeline.chunking import chunk_text
from kp.pipeline.plugin import Document
from kp.providers.ollama import OllamaClient


def embed_stage(
    doc: Document,
    *,
    store: EventStore,
    index: VectorIndex,
    client: OllamaClient | None = None,
) -> list[list[float]]:
    if not doc.text or not doc.text.strip():
        return []
    if index.has(doc.content_hash):
        return []

    client = client or OllamaClient()
    texts = chunk_text(doc.text)
    embeddings: list[list[float]] = []
    chunks_data: list[dict] = []

    for i, text in enumerate(texts):
        try:
            vec = client.embed(text)
        except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
            print(
                f"[embed_stage] WARNING: embed failed for chunk {i} of "
                f"{doc.content_hash!r}: {exc}. Skipping document."
            )
            return []
        embeddings.append(vec)
        chunks_data.append({"index": i, "text": text, "embedding": vec})

    index.upsert_chunks(doc.content_hash, doc.source, chunks_data)

    dim = len(embeddings[0]) if embeddings else 0
    store.append(
        EmbeddingCompleted(
            source=doc.source,
            content_hash=doc.content_hash,
            data={"dim": dim, "model": client.model, "chunks": len(chunks_data)},
        )
    )
    return embeddings
