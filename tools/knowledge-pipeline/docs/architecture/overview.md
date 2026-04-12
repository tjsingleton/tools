# Architecture Overview

The knowledge pipeline is a subdirectory tool (not its own repo) that ingests
personal signal into a curated, reviewable store. It is **event-sourced**,
**plugin-based**, and **budget-gated**.

## Data flow

```
source plugin.discover  -> RawDocument
     |
     v
plugin.load            (e.g. ffmpeg .qta -> .m4a)
     |
     v
transcribe backend     (faster-whisper default)
     |
     v
plugin.normalize       -> Document{text, metadata}
     |
     +--> analyze       (openrouter gpt-4o-mini, budget-gated)
     +--> embed         (ollama nomic-embed-text -> sqlite-vec)
     +--> curate        (DRY-RUN: writes ~/Library/KnowledgePipeline/review/)
```

Every stage appends events to a SQLite log; re-runs are idempotent by content_hash.

## Modules

| Module | Purpose |
|---|---|
| `kp.pipeline` | Runner + plugin protocol |
| `kp.pipeline.stages.*` | One file per stage |
| `kp.sources.voice_memo` | Voice memo plugin (m4a + qta) |
| `kp.events` | Append-only SQLite event log |
| `kp.budget` | Cost estimator + router (halt/hard cap) |
| `kp.providers.ollama` | Local embeddings |
| `kp.providers.openrouter` | LLM via openrouter |
| `kp.index.sqlite_vec` | Local vector store |
| `kp.ob1.client` | Thin MCP wrapper (disabled in dry-run) |
