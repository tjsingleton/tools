from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from kp.events import EventStore, SpeakerDiarized
from kp.pipeline.plugin import RawDocument
from kp.sources.voice_memo.diarize import DiarizationResult, get_diarizer


def diarize_stage(
    raw: RawDocument,
    *,
    store: EventStore,
    backend_name: str = "whisperx",
    backend=None,
) -> DiarizationResult | None:
    """Run speaker diarization. Idempotent via event-store hash check.

    Returns the DiarizationResult (loading from prior event if present),
    or None if backend can't run (e.g. missing HF token) — caller falls
    back to plain transcript.
    """
    if store.has_event(content_hash=raw.content_hash, event_type="SpeakerDiarized"):
        for row in store.all():
            if row["content_hash"] == raw.content_hash and row["event_type"] == "SpeakerDiarized":
                data = json.loads(row["data_json"])
                from kp.sources.voice_memo.diarize.backend import Segment

                segs = [Segment(**s) for s in data.get("segments", [])]
                return DiarizationResult(
                    segments=segs,
                    speakers=data.get("speakers", []),
                    metadata=data.get("metadata", {}),
                )

    backend = backend or get_diarizer(backend_name)
    result = backend.diarize(Path(raw.path))
    store.append(
        SpeakerDiarized(
            source=raw.source,
            content_hash=raw.content_hash,
            data={
                "segments": [asdict(s) for s in result.segments],
                "speakers": result.speakers,
                "backend": backend.name,
                "metadata": result.metadata,
            },
        )
    )
    return result
