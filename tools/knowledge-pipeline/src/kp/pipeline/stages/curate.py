from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from kp.events import EventStore, ItemCurated
from kp.pipeline.plugin import Document


REVIEW_DIR = Path.home() / "Library" / "KnowledgePipeline" / "review"
CONFIDENCE_THRESHOLD = 0.7


def curate_stage(
    doc: Document,
    *,
    analysis: dict[str, Any] | None,
    store: EventStore,
    review_dir: Path | None = None,
) -> dict[str, Any]:
    """DRY-RUN only. Writes proposed OB1 capture to review file. Never calls MCP."""
    outdir = Path(review_dir) if review_dir else REVIEW_DIR
    outdir.mkdir(parents=True, exist_ok=True)

    summary = (analysis or {}).get("summary", "") if analysis else ""
    confidence = float((analysis or {}).get("confidence", 0.0)) if analysis else 0.0
    action_items = (analysis or {}).get("action_items", []) if analysis else []
    should_promote = bool(summary.strip()) and confidence >= CONFIDENCE_THRESHOLD

    proposal = {
        "content_hash": doc.content_hash,
        "source": doc.source,
        "summary": summary,
        "confidence": confidence,
        "action_items": action_items,
        "should_promote": should_promote,
        "text_preview": doc.text[:500],
        "metadata": doc.metadata,
    }

    out_path = outdir / f"{date.today().isoformat()}.json"
    existing: list[dict[str, Any]] = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    # Replace any prior proposal for same content_hash (idempotent within day).
    existing = [p for p in existing if p.get("content_hash") != doc.content_hash]
    existing.append(proposal)
    out_path.write_text(json.dumps(existing, indent=2, default=str))

    store.append(
        ItemCurated(
            source=doc.source,
            content_hash=doc.content_hash,
            data={"should_promote": should_promote, "confidence": confidence, "review_file": str(out_path)},
        )
    )
    return proposal
