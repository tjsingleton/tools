# ADR 0004 — sqlite-vec for local embeddings

**Status:** Accepted

## Context
Need a local vector index. Options: pgvector (requires postgres), chroma,
lancedb, or sqlite-vec.

## Decision
`sqlite-vec` extension, with graceful fallback to storing embeddings as JSON
in a plain SQLite table when the extension can't be loaded.

## Consequences
- Zero-infra; one file (`~/Library/KnowledgePipeline/index.db`).
- Cosine similarity in-process when the extension loads.
- Portable across machines; trivial backup.
