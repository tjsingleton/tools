---
name: overnight-autorun
description: Run the knowledge-pipeline MVP-Vertical overnight against the voice memo corpus. Transcribes, analyzes, embeds, and curates (dry-run). Reviews land in ~/Library/KnowledgePipeline/review/.
triggers:
  - "overnight autorun"
  - "run knowledge pipeline"
  - "process voice memos"
---

# Overnight Autorun — Knowledge Pipeline

Runs the full voice memo pipeline against the dump directory with budget guardrails.

## Usage

```bash
cd /Volumes/DataDock/Users/tjsingleton/src/github.com/tjsingleton/tools/tools/knowledge-pipeline
uv run python main.py run \
  --source voice_memo \
  --path "/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP" \
  --stages ingest,normalize,transcribe,analyze,embed,curate \
  --budget-usd 4.50
```

## What it does
1. **Discovers** all .m4a and .qta files (converts .qta via ffmpeg)
2. **Transcribes** using faster-whisper (model: base, Metal-accelerated)
3. **Analyzes** with gpt-4o-mini via openrouter (budget-gated)
4. **Embeds** via ollama nomic-embed-text into local sqlite-vec
5. **Curates** (DRY-RUN): proposes OB1 captures → writes to `~/Library/KnowledgePipeline/review/`

## Budget
- Halt at $4.50, hard cap $5.00
- Per-item soft cap $0.25
- Check spend: `uv run python main.py budget status`

## Review outputs
```bash
# See curated proposals (DO NOT auto-promote without review)
cat ~/Library/KnowledgePipeline/review/$(date +%Y-%m-%d).json | jq .

# See event log
uv run python main.py events tail --source voice_memo
```

## Prerequisites
- ollama running: `ollama serve`
- openrouter key: `keyring set openrouter api_key` or `export OPENROUTER_API_KEY=...`
- ffmpeg: `brew install ffmpeg` (already installed)

## Source location
`tools/knowledge-pipeline/` in the tools repo.
Pipeline docs: `tools/knowledge-pipeline/docs/`
Full runbook: `tools/knowledge-pipeline/runbooks/overnight-run.md`
