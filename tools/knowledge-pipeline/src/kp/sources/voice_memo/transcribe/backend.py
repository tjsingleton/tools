from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class TranscriptionResult:
    text: str
    language: str = ""
    segments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class TranscribeBackend(Protocol):
    name: str

    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...
