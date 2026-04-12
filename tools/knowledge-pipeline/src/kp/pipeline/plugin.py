from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, runtime_checkable


@dataclass
class RawDocument:
    """Raw source item discovered by a plugin."""

    content_hash: str
    source: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Canonical, normalized document with text."""

    content_hash: str
    source: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SourcePlugin(Protocol):
    """Protocol for a source plugin (e.g. voice_memo, chatgpt_export)."""

    name: str

    def discover(self, path: Path) -> Iterable[RawDocument]: ...

    def load(self, raw: RawDocument) -> RawDocument: ...

    def normalize(self, raw: RawDocument) -> Document: ...
