# Overnight Run

Runs the full voice-memo pipeline against the dump corpus with budget guardrails.

## Prerequisites

### chromaprint (`fpcalc`)

Required for audio fingerprinting (deduplication and backfill).

```bash
brew install chromaprint
```

Verify: `which fpcalc`

### Backfill fingerprints for existing memos

After installing chromaprint, fingerprint all memos already in the event log.

**Dry-run first** (prints candidate count + duplicate-cluster preview, writes nothing):

```bash
cd tools/knowledge-pipeline
uv run python main.py voice-memo backfill-fingerprints --dry-run
```

**Commit the fingerprints** once the preview looks correct:

```bash
cd tools/knowledge-pipeline
uv run python main.py voice-memo backfill-fingerprints --no-dry-run
```

Idempotent: re-running is a no-op for already-fingerprinted entries.
The cluster report is written to `.omc/spikes/fingerprint-clusters-<YYYY-MM-DD>.json`.

## Command

```bash
cd tools/knowledge-pipeline
uv run python main.py run \
  --source voice_memo \
  --path "/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP" \
  --stages ingest,normalize,transcribe,diarize,analyze,embed,curate \
  --budget-usd 4.50
```

## What happens
1. **ingest** — SHA-256 hashes each audio file; skips anything already in the event log.
2. **normalize** — `.qta` → `.m4a` via ffmpeg (cached to `~/Library/KnowledgePipeline/cache/audio/`).
3. **transcribe** — `faster-whisper` model `base`. Transcript stored in `ItemTranscribed` event.
4. **diarize** — `whisperx` (faster-whisper + pyannote) labels speaker turns.
   `SpeakerDiarized` event stores `[{start, end, speaker_id, text}]`. Document
   text becomes `[SPEAKER_00] …\n[SPEAKER_01] …` so analyze sees turn-taking.
   Requires HF token (see Setup).
5. **analyze** — `gpt-4o-mini` via openrouter. Budget-gated; `BudgetDeferred` on soft cap.
6. **embed** — `nomic-embed-text` via ollama → `sqlite-vec` at `~/Library/KnowledgePipeline/index.db`.
7. **curate** — DRY-RUN only. Writes proposals to `~/Library/KnowledgePipeline/review/<YYYY-MM-DD>.json`.

## Setup
- HuggingFace token (needed for pyannote diarization model — accept ToS at
  https://huggingface.co/pyannote/speaker-diarization-3.1 first):
  ```
  security add-generic-password -s huggingface -a default -w
  ```
  Or `export HUGGINGFACE_TOKEN=hf_…` in the shell.
- OpenRouter key (analyze stage): `security add-generic-password -s openrouter -a default -w`
- Ollama: `ollama serve` + `ollama pull nomic-embed-text`

## Where things land
- Event log: `~/Library/KnowledgePipeline/events.db`
- Vector index: `~/Library/KnowledgePipeline/index.db`
- Audio cache: `~/Library/KnowledgePipeline/cache/audio/`
- **Review inbox**: `~/Library/KnowledgePipeline/review/`

## Monitoring
```bash
# live events
uv run python main.py events tail --source voice_memo

# budget state
uv run python main.py budget status

# curated proposals
uv run python main.py curate review
# or
cat ~/Library/KnowledgePipeline/review/$(date +%Y-%m-%d).json | jq .
```

## If budget halts
`BudgetDeferred` events are emitted; rerun after raising `--budget-usd` or clearing
`total_spent_usd` tracking. The pipeline is idempotent — already-completed stages
will not re-bill.

## Review UI

After backfill, browse extractions:

```bash
uv run python main.py serve --port 8765
# open http://127.0.0.1:8765/
```

Three pages:
- `/` — memo index (filterable by source, by speaker count)
- `/memo/{hash}` — detail page with audio player, speaker-grouped transcript with click-to-seek timestamps, side-by-side MacWhisper VTT or polished .md, raw-events expandable
- `/status` — pipeline state: per-stage counts, recent events, total OpenRouter spend (auto-refreshes every 5s)

## Fetching new memos

Pull new audio from the Voice Memos.app:

```bash
uv run python main.py fetch
```

Idempotent via SHA-256.
