from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from kp.budget import BudgetRouter, estimate_cost_usd
from kp.events import AnalysisCompleted, BudgetDeferred, EventStore
from kp.pipeline.plugin import Document
from kp.providers.openrouter import OpenRouterClient


class ActionItem(BaseModel):
    text: str
    speaker: str | None = None  # speaker_id from diarization, e.g. "SPEAKER_00", or None


class VoiceMemoAnalysis(BaseModel):
    summary: str = ""
    action_items: list[ActionItem] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    speakers: list[str] = Field(default_factory=list)  # diarized speaker_ids present
    topics: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    memo_type: str = "note"  # decision | idea | note | todo | personal


SYSTEM_PROMPT = (
    "You are analyzing a personal voice memo transcript. The transcript may be "
    "speaker-labeled (lines like '[SPEAKER_00] ...'); when it is, attribute action "
    "items to the speaker who committed to them. "
    "Respond with a single JSON object with keys: summary, action_items "
    "(list of {text, speaker}), people, speakers (list of speaker_ids present), "
    "topics, dates, confidence (0-1), memo_type."
)


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except Exception:
        # strip code fences
        s = content.strip().strip("`")
        if s.startswith("json"):
            s = s[4:]
        return json.loads(s)


def analyze_stage(
    doc: Document,
    *,
    store: EventStore,
    budget: BudgetRouter,
    client: OpenRouterClient | None = None,
    model: str = "openai/gpt-4o-mini",
) -> VoiceMemoAnalysis | None:
    """Returns analysis or None if budget-deferred / empty input."""
    if not doc.text or not doc.text.strip():
        return None

    estimated = estimate_cost_usd(model=model, input_text=doc.text, expected_output_tokens=300)
    allowed, reason = budget.can_spend(estimated)
    if not allowed:
        store.append(
            BudgetDeferred(
                source=doc.source,
                content_hash=doc.content_hash,
                data={"reason": reason, "estimated_cost_usd": estimated, "stage": "analyze"},
            )
        )
        return None

    client = client or OpenRouterClient(model=model)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": doc.text},
    ]
    resp = client.chat(messages, response_format={"type": "json_object"})
    content = resp["choices"][0]["message"]["content"]
    parsed = _parse_json(content)
    # Normalize legacy action_items: list[str] -> list[ActionItem]
    items = parsed.get("action_items") or []
    parsed["action_items"] = [
        {"text": it, "speaker": None} if isinstance(it, str) else it for it in items
    ]
    analysis = VoiceMemoAnalysis(**parsed)

    # Record actual cost (use usage if present, else estimated).
    usage = resp.get("usage") or {}
    if usage:
        prices = {"openai/gpt-4o-mini": {"input_per_m": 0.15, "output_per_m": 0.60}}
        mp = prices.get(model, {"input_per_m": 0.15, "output_per_m": 0.60})
        cost = (
            usage.get("prompt_tokens", 0) / 1_000_000 * mp["input_per_m"]
            + usage.get("completion_tokens", 0) / 1_000_000 * mp["output_per_m"]
        )
    else:
        cost = estimated
    budget.record(cost)

    store.append(
        AnalysisCompleted(
            source=doc.source,
            content_hash=doc.content_hash,
            data={
                "analysis": analysis.model_dump(),
                "cost_usd": round(cost, 6),
                "model": model,
            },
        )
    )
    return analysis
