from __future__ import annotations

from kp.pipeline.plugin import Document, RawDocument


def normalize(raw: RawDocument, *, text: str | None = None) -> Document:
    """Produce canonical Document. If `text` not provided, leave empty (transcribe stage fills it)."""
    metadata = dict(raw.metadata)
    metadata["path"] = str(raw.path)
    return Document(
        content_hash=raw.content_hash,
        source=raw.source,
        text=text or "",
        metadata=metadata,
    )
