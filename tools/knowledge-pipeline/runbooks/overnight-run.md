# Overnight Run

Runs the full voice-memo pipeline against the dump corpus with budget guardrails.

## Command

```bash
cd tools/knowledge-pipeline
uv run python main.py run \
  --source voice_memo \
  --path "/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP" \
  --stages ingest,normalize,transcribe,analyze,embed,curate \
  --budget-usd 4.50
```

## What happens
1. **ingest** — SHA-256 hashes each audio file; skips anything already in the event log.
2. **normalize** — `.qta` → `.m4a` via ffmpeg (cached to `~/Library/KnowledgePipeline/cache/audio/`).
3. **transcribe** — `faster-whisper` model `base`. Transcript stored in `ItemTranscribed` event.
4. **analyze** — `gpt-4o-mini` via openrouter. Budget-gated; `BudgetDeferred` on soft cap.
5. **embed** — `nomic-embed-text` via ollama → `sqlite-vec` at `~/Library/KnowledgePipeline/index.db`.
6. **curate** — DRY-RUN only. Writes proposals to `~/Library/KnowledgePipeline/review/<YYYY-MM-DD>.json`.

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
