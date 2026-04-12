# AGENTS.md — knowledge-pipeline

Scope: `tools/knowledge-pipeline/` — personal knowledge ingestion pipeline.

## Quick orientation
- Entry point: `main.py` -> `kp.cli:cli`.
- Plugin protocol: `kp.pipeline.plugin.SourcePlugin` (discover/load/normalize).
- Source plugins live under `kp.sources.<name>`. Only `voice_memo` is implemented.
- Stages live under `kp.pipeline.stages/`. They are composable and event-sourced.
- All state changes are events in SQLite (`~/Library/KnowledgePipeline/events.db`).
- Embeddings are stored locally via `sqlite-vec` (fallback: JSON column).

## Safety invariants (do not break)
1. **Curate is DRY-RUN ONLY.** Never import/call OB1 MCP from `stages/curate.py`.
2. **Budget gates every paid call.** `BudgetRouter.can_spend(...)` before any openrouter call.
3. **Ingestion is idempotent** via `EventStore.has_event(content_hash=..., event_type=...)`.
4. **Raw audio never committed** — see `.gitignore`.

## Commands
- `uv run pytest -q` — unit + BDD tests.
- `uv run python main.py run --source voice_memo --path <dir>` — full pipeline.
- `uv run python main.py events tail --source voice_memo` — see event log.
- `uv run python main.py curate review` — inspect pending dry-run proposals.

## Adding a new source plugin
1. Create `src/kp/sources/<name>/` with `discover.py`, `load.py`, `normalize.py`.
2. Export a class matching `SourcePlugin` Protocol from the package `__init__.py`.
3. Register it in `kp.cli._get_plugin`.
