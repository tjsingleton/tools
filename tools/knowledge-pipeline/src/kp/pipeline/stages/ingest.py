from __future__ import annotations

from pathlib import Path
from typing import Iterator

from kp.events import EventStore, ItemIngested
from kp.pipeline.plugin import RawDocument


def ingest_stage(plugin, path: Path, store: EventStore) -> Iterator[RawDocument]:
    """Discover items from plugin. Skip any content_hash already ingested."""
    for raw in plugin.discover(path):
        if store.has_event(content_hash=raw.content_hash, event_type="ItemIngested"):
            continue
        store.append(
            ItemIngested(
                source=raw.source,
                content_hash=raw.content_hash,
                data={"path": str(raw.path), "metadata": raw.metadata},
            )
        )
        yield raw
