from __future__ import annotations

import logging
import os
import platform
from pathlib import Path

from kp.sources.voice_memo.diarize.backend import DiarizationResult, Segment

log = logging.getLogger(__name__)


def _hf_token() -> str | None:
    tok = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
    if tok:
        return tok
    try:
        import keyring  # type: ignore

        return keyring.get_password("huggingface", "default")
    except Exception:
        return None


def _resolve_device(device: str) -> str:
    """Resolve ``"auto"`` to the best available device.

    On Apple Silicon, prefers ``"mps"`` when ``torch.backends.mps.is_available()``
    returns True; otherwise falls back to ``"cpu"``.
    """
    if device != "auto":
        return device

    is_arm = platform.machine() == "arm64"
    if is_arm:
        try:
            import torch  # type: ignore

            if torch.backends.mps.is_available():
                log.debug("device=auto → mps (Apple Silicon)")
                return "mps"
        except Exception:
            pass

    log.debug("device=auto → cpu")
    return "cpu"


class WhisperXBackend:
    name = "whisperx"

    def __init__(
        self,
        *,
        model: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        language: str | None = "en",
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        hf_token: str | None = None,
    ) -> None:
        self.model_name = model
        self.device = _resolve_device(device)
        self.compute_type = compute_type
        self.language = language
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.hf_token = hf_token or _hf_token()
        self._asr = None
        self._diar = None
        self._align_model = None
        self._align_meta = None
        self._align_lang: str | None = None

    def _load_asr(self):
        if self._asr is None:
            import whisperx  # type: ignore

            # ctranslate2 only supports cpu/cuda; MPS is used only for pyannote/align models
            asr_device = "cpu" if self.device == "mps" else self.device
            self._asr = whisperx.load_model(
                self.model_name, asr_device, compute_type=self.compute_type
            )
        return self._asr

    def _load_diar(self):
        if self._diar is None:
            if not self.hf_token:
                raise RuntimeError(
                    "WhisperX diarization requires a HuggingFace token. "
                    "Set HUGGINGFACE_TOKEN or store via "
                    "`security add-generic-password -s huggingface -a default -w`."
                )
            from whisperx.diarize import DiarizationPipeline  # type: ignore

            self._diar = DiarizationPipeline(
                token=self.hf_token, device=self.device
            )
        return self._diar

    def diarize(self, audio_path: Path) -> DiarizationResult:
        import whisperx  # type: ignore

        audio = whisperx.load_audio(str(audio_path))
        asr = self._load_asr()
        result = asr.transcribe(audio, language=self.language) if self.language else asr.transcribe(audio)
        lang = result.get("language", "")

        if self._align_lang != lang or self._align_model is None:
            self._align_model, self._align_meta = whisperx.load_align_model(language_code=lang, device=self.device)
            self._align_lang = lang
        align_model, align_meta = self._align_model, self._align_meta
        aligned = whisperx.align(
            result["segments"], align_model, align_meta, audio, self.device,
            return_char_alignments=False,
        )

        diar = self._load_diar()
        try:
            diar_segments = diar(
                audio, min_speakers=self.min_speakers, max_speakers=self.max_speakers
            )
        except RuntimeError as exc:
            msg = str(exc)
            if self.device == "mps" and ("mps" in msg.lower() or "aten::" in msg):
                log.warning(
                    "MPS diarization failed (%s); retrying on CPU.", exc
                )
                self.device = "cpu"
                self._diar = None
                self._align_model = None
                self._align_meta = None
                self._align_lang = None
                diar = self._load_diar()
                diar_segments = diar(
                    audio,
                    min_speakers=self.min_speakers,
                    max_speakers=self.max_speakers,
                )
            else:
                raise
        with_speakers = whisperx.assign_word_speakers(diar_segments, aligned)

        segs: list[Segment] = []
        speakers: set[str] = set()
        for s in with_speakers.get("segments", []):
            spk = s.get("speaker") or "SPEAKER_UNKNOWN"
            speakers.add(spk)
            segs.append(
                Segment(
                    start=float(s.get("start", 0.0)),
                    end=float(s.get("end", 0.0)),
                    speaker_id=spk,
                    text=str(s.get("text", "")).strip(),
                )
            )
        return DiarizationResult(
            segments=segs,
            speakers=sorted(speakers),
            metadata={"model": self.model_name, "language": lang},
        )
