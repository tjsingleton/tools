# ADR 0007 — Dual-layer dictionary biasing (planned)

**Status:** Proposed (stubbed in MVP)

## Context
Personal names/places/jargon are often mis-transcribed. We want to bias the
transcriber and fuzzy-correct outputs using a personal vocabulary.

## Decision
Two layers:
1. **Hot vocab (hint prompt)** — pass as `initial_prompt` to faster-whisper.
2. **Post-hoc fuzzy correction** — `rapidfuzz` against a lexicon sourced from
   PKB/OB1 via `kp.vocab.lookup.lookup_terms` (currently stubbed to `[]`).

## Consequences
- In MVP, `lookup_terms` returns `[]` so no biasing is applied.
- Wiring is in place: when PKB/OB1 exposes the lexicon, we populate both layers.
- Tests pin the current behavior (empty lexicon passes through).
