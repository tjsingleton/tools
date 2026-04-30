from __future__ import annotations

from kp.events import EventStore, ItemNormalized
from kp.pipeline.plugin import RawDocument


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
