from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from kp.budget import BudgetRouter
from kp.events import EventStore, ItemTranscribed
from kp.pipeline.plugin import Document, RawDocument
from kp.pipeline.stages.analyze import analyze_stage
from kp.pipeline.stages.curate import curate_stage
from kp.pipeline.stages.embed import embed_stage
from kp.pipeline.stages.ingest import ingest_stage
from kp.pipeline.stages.normalize import normalize_stage


log = structlog.get_logger()


class PipelineRunner:
    def __init__(
        self,
        *,
        plugin,
        dry_run: bool = True,
        halt_usd: float = 4.50,
        hard_cap_usd: float = 5.00,
        per_item_soft_cap: float = 0.25,
        transcribe_backend: str = "faster_whisper",
        event_store: EventStore | None = None,
    ) -> None:
        self.plugin = plugin
        self.dry_run = dry_run
        self.budget = BudgetRouter(
            halt_usd=halt_usd,
            hard_cap_usd=hard_cap_usd,
            per_item_soft_cap=per_item_soft_cap,
        )
        self.transcribe_backend_name = transcribe_backend
        self.store = event_store or EventStore()
        self._index = None
        self._transcribe_backend = None

    def _get_index(self):
        if self._index is None:
            from kp.index.sqlite_vec import VectorIndex

            self._index = VectorIndex()
        return self._index

    def _get_transcribe_backend(self):
        if self._transcribe_backend is None:
            from kp.sources.voice_memo.transcribe import get_backend

            self._transcribe_backend = get_backend(self.transcribe_backend_name)
        return self._transcribe_backend

    def _transcribe(self, raw: RawDocument) -> str:
        if self.store.has_event(content_hash=raw.content_hash, event_type="ItemTranscribed"):
            # look up prior transcript from events
            for row in self.store.all():
                if row["content_hash"] == raw.content_hash and row["event_type"] == "ItemTranscribed":
                    import json as _json

                    return _json.loads(row["data_json"]).get("text", "")
            return ""
        backend = self._get_transcribe_backend()
        result = backend.transcribe(Path(raw.path))
        self.store.append(
            ItemTranscribed(
                source=raw.source,
                content_hash=raw.content_hash,
                data={
                    "text": result.text,
                    "language": result.language,
                    "backend": backend.name,
                    "metadata": result.metadata,
                },
            )
        )
        return result.text

    def _make_document(self, raw: RawDocument, text: str) -> Document:
        try:
            return self.plugin.normalize(raw, text=text)  # type: ignore[call-arg]
        except TypeError:
            doc = self.plugin.normalize(raw)
            doc.text = text
            return doc

    def run(self, *, path: Path, stages: list[str]) -> dict[str, Any]:
        counts = {s: 0 for s in stages}
        counts["items"] = 0

        for raw in ingest_stage(self.plugin, path, self.store):
            counts["ingest"] = counts.get("ingest", 0) + 1
            counts["items"] += 1

            loaded = raw
            if "normalize" in stages:
                loaded = normalize_stage(self.plugin, raw, self.store)
                counts["normalize"] += 1

            text = ""
            if "transcribe" in stages:
                text = self._transcribe(loaded)
                counts["transcribe"] += 1

            doc = self._make_document(loaded, text)

            analysis_dict: dict[str, Any] | None = None
            if "analyze" in stages:
                analysis = analyze_stage(doc, store=self.store, budget=self.budget)
                if analysis is not None:
                    analysis_dict = analysis.model_dump()
                    counts["analyze"] += 1

            if "embed" in stages:
                emb = embed_stage(doc, store=self.store, index=self._get_index())
                if emb:
                    counts["embed"] += 1

            if "curate" in stages:
                curate_stage(doc, analysis=analysis_dict, store=self.store)
                counts["curate"] += 1

        return {
            "stages": stages,
            "counts": counts,
            "budget": self.budget.status(),
            "dry_run": self.dry_run,
        }
