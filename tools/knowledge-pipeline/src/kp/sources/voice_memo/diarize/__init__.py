from kp.sources.voice_memo.diarize.backend import DiarizeBackend, DiarizationResult, Segment
from kp.sources.voice_memo.diarize.whisperx_backend import WhisperXBackend


def get_diarizer(name: str = "whisperx", **kwargs) -> DiarizeBackend:
    if name == "whisperx":
        return WhisperXBackend(**kwargs)
    raise ValueError(f"Unknown diarize backend: {name}")


__all__ = [
    "DiarizeBackend",
    "DiarizationResult",
    "Segment",
    "WhisperXBackend",
    "get_diarizer",
]
