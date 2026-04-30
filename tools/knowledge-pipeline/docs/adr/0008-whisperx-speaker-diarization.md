# ADR 0008 — WhisperX for speaker diarization

**Status:** Accepted (2026-04-29)

## Context

Some voice memos are multi-party (recorded meetings/calls/conversations).
A single-stream transcript without speaker labels collapses turn-taking and
loses attribution signal that downstream analyze/curate stages need
(e.g. "TJ said he'd email Nate" → structured action item).

Candidates evaluated:

| Stack | Notes |
|---|---|
| `pyannote.audio` 3.x + faster-whisper (manual alignment) | Industry standard; full control; we'd write the alignment glue ourselves. HF-gated model. |
| `whisperx` | Wraps faster-whisper + pyannote + word-level alignment in one library. Same HF-gating constraint. Less code. |
| `nemo-toolkit` (NVIDIA Sortformer) | Newer, claims better short-segment performance. Heavy dep, uneven Apple Silicon support. |
| `diart` | Streaming/online; overkill for batch. |

## Decision

Use **WhisperX** as the diarization backend behind a `get_diarizer(name)`
factory that mirrors the existing `get_backend()` transcription pattern.

Rationale:
- Single dependency that bundles the three things we need: faster-whisper
  inference, word-level alignment, and pyannote diarization.
- Reuses the model we already chose in ADR 0006.
- Backend-swap escape hatch keeps us free to drop down to raw
  pyannote if WhisperX becomes a bottleneck.

## Consequences

- New dep: `whisperx` (pulls in `pyannote.audio`, `torch`, alignment models).
- HuggingFace token required to accept the pyannote ToS; stored in
  keychain under service `huggingface`, account `default` (parallel to
  ADR-conformant `openrouter` storage).
- Diarization runs locally; no OpenRouter cost impact.
- New event `SpeakerDiarized` is emitted between `ItemTranscribed` and
  `AnalysisCompleted`, hash-keyed for idempotency.
- `Document.text` for voice_memo is assembled as
  `"[Speaker A] …\n[Speaker B] …"` when diarization ran, so the analyze
  prompt can reason about turn-taking. ChatGPT-export and other
  text-only sources skip diarize cleanly (it's source-scoped, not global).
- Apple Silicon performance: pyannote on MPS is ~2–5× realtime on
  M-series; acceptable for the 6-file batch. CPU fallback works.
