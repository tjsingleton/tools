from __future__ import annotations

from pathlib import Path

from kp.sources.voice_memo.transcribe.backend import TranscriptionResult


class PyWhisperCppBackend:
    """Stub. Raises ImportError if pywhispercpp is not installed."""

    name = "pywhispercpp"

    def __init__(self, *, model_path: str | None = None, **_: object) -> None:
        self.model_path = model_path
        try:
            import pywhispercpp  # type: ignore # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pywhispercpp backend is not installed. Install pywhispercpp or use faster_whisper."
            ) from e

    def transcribe(self, audio_path: Path) -> TranscriptionResult:  # pragma: no cover
        raise NotImplementedError("pywhispercpp backend not implemented in MVP-Vertical")
