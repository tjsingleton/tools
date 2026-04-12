from __future__ import annotations

import json
from pathlib import Path

from kp.events import EventStore
from kp.pipeline.plugin import Document
from kp.pipeline.stages.curate import curate_stage


def test_curate_writes_review_file(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    review = tmp_path / "review"
    doc = Document(content_hash="h1", source="voice_memo", text="Discussed hiring Jane on Tuesday.", metadata={})
    analysis = {"summary": "Hiring decision", "confidence": 0.9, "action_items": ["Email Jane"]}
    result = curate_stage(doc, analysis=analysis, store=store, review_dir=review)
    assert result["should_promote"] is True
    files = list(review.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload[0]["content_hash"] == "h1"
    store.close()


def test_curate_low_confidence_not_promoted(tmp_path: Path):
    store = EventStore(db_path=tmp_path / "e.db")
    review = tmp_path / "review"
    doc = Document(content_hash="h2", source="voice_memo", text="mumble", metadata={})
    result = curate_stage(doc, analysis={"summary": "x", "confidence": 0.3}, store=store, review_dir=review)
    assert result["should_promote"] is False
    store.close()


def test_curate_never_calls_ob1(tmp_path: Path):
    # Curate stage does not import or invoke OB1Client at all; smoke check.
    store = EventStore(db_path=tmp_path / "e.db")
    doc = Document(content_hash="h3", source="voice_memo", text="t", metadata={})
    curate_stage(doc, analysis=None, store=store, review_dir=tmp_path / "r")
    store.close()
