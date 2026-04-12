from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    event_type: str = ""
    source: str = ""
    content_hash: str = ""
    timestamp: str = field(default_factory=_now)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ItemIngested(Event):
    event_type: str = "ItemIngested"


@dataclass
class ItemNormalized(Event):
    event_type: str = "ItemNormalized"


@dataclass
class ItemTranscribed(Event):
    event_type: str = "ItemTranscribed"


@dataclass
class AnalysisCompleted(Event):
    event_type: str = "AnalysisCompleted"


@dataclass
class EmbeddingCompleted(Event):
    event_type: str = "EmbeddingCompleted"


@dataclass
class ItemCurated(Event):
    event_type: str = "ItemCurated"


@dataclass
class BudgetDeferred(Event):
    event_type: str = "BudgetDeferred"
