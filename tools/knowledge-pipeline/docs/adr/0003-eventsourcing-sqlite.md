# ADR 0003 — Event sourcing on SQLite

**Status:** Accepted

## Context
We need durability, idempotency, and auditable reruns. Options: append-only
JSONL files, a lightweight event-sourcing lib, or a SQLite append-only table.

## Decision
Plain SQLite table `events(id, timestamp, event_type, source, content_hash, data_json)`.
No ORM, no migrations framework. Dataclasses for the event types.

## Consequences
- Idempotency check is a single `SELECT ... WHERE content_hash = ? AND event_type = ?`.
- Stdlib only for the store; no extra dep.
- Future: we can project events into read models as needed.
