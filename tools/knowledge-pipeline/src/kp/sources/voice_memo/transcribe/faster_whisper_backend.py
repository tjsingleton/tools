from __future__ import annotations

from pathlib import Path

from kp.sources.voice_memo.transcribe.backend import TranscriptionResult


class FasterWhisperBackend:
    name = "faster_whisper"

    def __init__(
        self,
        *,
        model: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        language: str | None = None,
    ) -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore

            self._model = WhisperModel(
                self.model_name, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        model = self._load()
        segments, info = model.transcribe(str(audio_path), language=self.language)
        seg_list = []
        text_parts = []
        for s in segments:
            seg_list.append(
                {"start": float(s.start), "end": float(s.end), "text": s.text}
            )
            text_parts.append(s.text)
        return TranscriptionResult(
            text="".join(text_parts).strip(),
            language=getattr(info, "language", "") or "",
            segments=seg_list,
            metadata={
                "model": self.model_name,
                "duration": float(getattr(info, "duration", 0.0) or 0.0),
            },
        )
