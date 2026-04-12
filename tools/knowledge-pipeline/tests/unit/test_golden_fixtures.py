from __future__ import annotations

import json
from pathlib import Path

from kp.pipeline.stages.analyze import VoiceMemoAnalysis


GOLDEN = Path(__file__).parent.parent / "fixtures" / "golden" / "voice_memo"


def test_sample_transcript_exists():
    assert (GOLDEN / "sample.md").exists()
    text = (GOLDEN / "sample.md").read_text()
    assert len(text) > 50


def test_sample_analysis_matches_schema():
    data = json.loads((GOLDEN / "sample_analysis.json").read_text())
    # Validates shape matches VoiceMemoAnalysis.
    analysis = VoiceMemoAnalysis(**data)
    assert analysis.summary
    assert 0.0 <= analysis.confidence <= 1.0
    assert analysis.memo_type in {"decision", "idea", "note", "todo", "personal"}
