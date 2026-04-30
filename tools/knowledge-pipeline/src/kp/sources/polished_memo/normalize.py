from __future__ import annotations

from pathlib import Path

from kp.pipeline.plugin import Document, RawDocument


def normalize(raw: RawDocument, *, text: str | None = None) -> Document:
    """Produce canonical Document with full markdown body as text."""
    if text is None:
        text = Path(raw.path).read_text(encoding="utf-8")
    metadata = dict(raw.metadata)
    metadata["path"] = str(raw.path)
    return Document(
        content_hash=raw.content_hash,
        source=raw.source,
        text=text,
        metadata=metadata,
    )
