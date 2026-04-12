from kp.sources.voice_memo.transcribe.backend import TranscribeBackend, TranscriptionResult
from kp.sources.voice_memo.transcribe.faster_whisper_backend import FasterWhisperBackend
from kp.sources.voice_memo.transcribe.pywhispercpp_backend import PyWhisperCppBackend


def get_backend(name: str = "faster_whisper", **kwargs) -> TranscribeBackend:
    if name == "faster_whisper":
        return FasterWhisperBackend(**kwargs)
    if name == "pywhispercpp":
        return PyWhisperCppBackend(**kwargs)
    raise ValueError(f"Unknown transcribe backend: {name}")


__all__ = [
    "TranscribeBackend",
    "TranscriptionResult",
    "FasterWhisperBackend",
    "PyWhisperCppBackend",
    "get_backend",
]
