from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class Segment:
    start: float
    end: float
    speaker_id: str
    text: str


@dataclass
class DiarizationResult:
    segments: list[Segment] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def assemble_text(self) -> str:
        """Render diarized segments as `[Speaker A] …\\n[Speaker B] …`."""
        out: list[str] = []
        last_spk: str | None = None
        buf: list[str] = []
        for seg in self.segments:
            if seg.speaker_id != last_spk:
                if buf and last_spk is not None:
                    out.append(f"[{last_spk}] {' '.join(buf).strip()}")
                buf = [seg.text.strip()]
                last_spk = seg.speaker_id
            else:
                buf.append(seg.text.strip())
        if buf and last_spk is not None:
            out.append(f"[{last_spk}] {' '.join(buf).strip()}")
        return "\n".join(out)


@runtime_checkable
class DiarizeBackend(Protocol):
    name: str

    def diarize(self, audio_path: Path) -> DiarizationResult: ...
