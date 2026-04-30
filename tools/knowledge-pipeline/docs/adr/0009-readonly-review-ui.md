# ADR 0009 — Read-only review UI; MacWhisper as visual reference, not merge target

**Status:** Accepted (2026-04-29)

## Context

The kp pipeline produces transcribed + diarized + analyzed events for voice memos.
A prior MacWhisper + `/transcript-polisher` workflow produced ~69 polished `.md`
transcripts plus paired `.vtt` files. To iterate fast on extraction quality, we need
a way to review pipeline output and compare it visually against the prior MacWhisper corpus.

## Decision

Build a read-only FastAPI web UI at `localhost:8765` (`kp serve`) that:
- Lists memos sorted by date with filters (source, multi-speaker).
- Detail page shows our transcript + structured analysis on the left; MacWhisper
  VTT or polished `.md` (found via metadata pairing) on the right.
- No edit endpoints. State changes only via pipeline re-run.
- Visual side-by-side only; no auto-diff or semantic comparison in this iteration.

## Alternatives Considered

| Option | Rationale |
|---|---|
| Editable UI from day one | Write-back semantics (compensating events vs new event types vs amend) are non-trivial; user chose read-only first. |
| Static HTML report (`kp report`) | Single-pass only; user wants re-run + refresh as a tight loop. |
| TUI (Textual) | Side-by-side visual diff is awkward; sharing/linking doesn't work well. |
| Auto-diff (word-level vs MacWhisper) | Deferred; visual comparison surfaces error clusters faster initially. |

## Consequences

- New deps: fastapi, uvicorn, jinja2, markdown.
- Web tree (`src/kp/web/`) is isolated; can be removed/replaced without touching
  the pipeline core.
- MacWhisper pairing via `voice_memo_transcript_pairs_canonical.json` (enriched in
  voice_memo plugin discover step).
- Editable UI, write-back, embed stage, and OB1 publish remain non-goals for this iteration.
