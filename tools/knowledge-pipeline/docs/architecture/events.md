# Events

The pipeline is **event-sourced**: every stage appends a row to
`~/Library/KnowledgePipeline/events.db`. No row is ever mutated.

## Schema

```sql
CREATE TABLE events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,      -- ISO8601 UTC
    event_type   TEXT NOT NULL,      -- dataclass name
    source       TEXT NOT NULL,      -- e.g. voice_memo
    content_hash TEXT NOT NULL,      -- SHA-256 of raw item
    data_json    TEXT NOT NULL       -- JSON payload
);
```

## Event types
- `ItemIngested` — discovered by plugin.
- `ItemNormalized` — loaded (e.g. transcoded).
- `ItemTranscribed` — transcript available.
- `AnalysisCompleted` — LLM analysis stored.
- `EmbeddingCompleted` — vector indexed.
- `ItemCurated` — dry-run proposal written.
- `BudgetDeferred` — skipped due to budget.

## Idempotency
Stages call `EventStore.has_event(content_hash, event_type)` to short-circuit
repeat work. Re-running the pipeline is safe.
