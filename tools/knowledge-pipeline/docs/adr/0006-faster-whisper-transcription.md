# ADR 0006 — faster-whisper (model: base) as transcription default

**Status:** Accepted

## Context
No MacWhisper GGML model is present on disk, so `pywhispercpp` would require
a separate install + model download. `faster-whisper` auto-downloads the CT2
model and works out of the box.

## Decision
Default backend: `faster_whisper` with model `base`, `compute_type=int8`,
`device=auto`. Keep `pywhispercpp` as a selectable backend for future use.

## Consequences
- Works on Apple Silicon without setup.
- Can swap to pywhispercpp via config (`model_backend: "pywhispercpp"`).
- Transcription cost is purely CPU/GPU time; not budget-gated.
