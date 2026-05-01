from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import structlog

from kp.events import AudioFingerprinted, EventStore, ItemIngested
from kp.pipeline.plugin import RawDocument

log = structlog.get_logger()


def ingest_stage(plugin, path: Path, store: EventStore) -> Iterator[RawDocument]:
    """Discover items from plugin. Skip any content_hash already ingested.

    For voice_memo items, emits a sibling AudioFingerprinted event immediately
    after each ItemIngested, preserving the invariant that every voice_memo
    ItemIngested has a corresponding AudioFingerprinted row.
    """
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

        if raw.source == "voice_memo":
            if raw.audio_fingerprint is not None:
                duration, fp_str = raw.audio_fingerprint
                # Determine the audio path that was actually fingerprinted:
                # .qta sources are fingerprinted via the cache .m4a; .m4a sources directly.
                if raw.path.suffix.lower() == ".qta":
                    from kp.sources.voice_memo.load import CACHE_DIR
                    audio_path = str(CACHE_DIR / f"{raw.content_hash}.m4a")
                else:
                    audio_path = str(raw.path)
                store.append(
                    AudioFingerprinted(
                        content_hash=raw.content_hash,
                        source="voice_memo",
                        data={
                            "audio_fingerprint": fp_str,
                            "audio_duration": duration,
                            "audio_path": audio_path,
                            "computed_by": "ingest",
                        },
                    )
                )
            else:
                log.warning(
                    "ingest.missing_audio_fingerprint",
                    content_hash=raw.content_hash,
                    source=raw.source,
                )

        yield raw


def reprocess_stage(
    store: EventStore,
    *,
    source: str | None = None,
) -> Iterator[RawDocument]:
    """Yield RawDocument for items already ingested+normalized.

    Reads the latest `ItemNormalized` event per content_hash so the yielded
    `path` points at the post-conversion cached `.m4a` (not the original .qta).
    Used by `PipelineRunner.run(reprocess=True)` to backfill later stages
    (e.g. diarize, analyze) without re-running ingest/normalize.
    """
    seen: set[str] = set()
    # iterate newest-first so we get the most recent normalize per hash
    rows = sorted(store.all(), key=lambda r: r["id"], reverse=True)
    for row in rows:
        if row["event_type"] != "ItemNormalized":
            continue
        if source is not None and row["source"] != source:
            continue
        ch = row["content_hash"]
        if ch in seen:
            continue
        seen.add(ch)
        data = json.loads(row["data_json"])
        yield RawDocument(
            content_hash=ch,
            source=row["source"],
            path=Path(data["path"]),
            metadata=data.get("metadata", {}),
        )

    # Yield ItemIngested items that never got ItemNormalized (pipeline gap recovery)
    normalized_hashes = {
        row["content_hash"]
        for row in store.all()
        if row["event_type"] == "ItemNormalized"
    }
    for row in store.all():
        if row["event_type"] != "ItemIngested":
            continue
        if source is not None and row["source"] != source:
            continue
        ch = row["content_hash"]
        if ch in seen:
            continue
        if ch in normalized_hashes:
            continue
        data = json.loads(row["data_json"])
        path_str = data.get("path") or data.get("metadata", {}).get("path", "")
        if not path_str:
            continue
        seen.add(ch)
        yield RawDocument(
            content_hash=ch,
            source=row.get("source", source or ""),
            path=Path(path_str),
            metadata=data.get("metadata", {}),
        )
