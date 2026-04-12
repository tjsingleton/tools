from __future__ import annotations

from kp.events import EventStore, ItemNormalized
from kp.pipeline.plugin import Document, RawDocument


def normalize_stage(plugin, raw: RawDocument, store: EventStore) -> RawDocument:
    """Load (e.g. convert .qta->.m4a) and emit ItemNormalized event. Returns loaded raw."""
    loaded = plugin.load(raw)
    store.append(
        ItemNormalized(
            source=loaded.source,
            content_hash=loaded.content_hash,
            data={"path": str(loaded.path), "metadata": loaded.metadata},
        )
    )
    return loaded


def make_document(plugin, raw: RawDocument, *, text: str) -> Document:
    # Normalize to canonical Document, injecting transcribed text.
    return plugin.normalize(raw) if text == "" else plugin.normalize.__self__ if False else _normalize_with_text(plugin, raw, text)


def _normalize_with_text(plugin, raw: RawDocument, text: str) -> Document:
    # Prefer plugin.normalize(raw, text=text) if it accepts text.
    try:
        return plugin.normalize(raw, text=text)  # type: ignore[call-arg]
    except TypeError:
        doc = plugin.normalize(raw)
        doc.text = text
        return doc
