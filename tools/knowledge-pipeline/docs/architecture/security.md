# Security

## Secrets
- `openrouter` API key: fetched from macOS keyring (`keyring.get_password("openrouter", "api_key")`).
- Fallback: `OPENROUTER_API_KEY` environment variable.
- Never logged, never committed, never included in events.

## Local data
- Audio corpus lives on disk only; `.gitignore` excludes `*.m4a`, `*.mp3`, `*.wav`, `*.qta`.
- Event log, vector index, and review proposals live under `~/Library/KnowledgePipeline/` (outside git).

## OB1 isolation
- The curate stage writes JSON proposals to disk only.
- `OB1Client` exists but is disabled (`dry_run=True`). `capture_thought` refuses to run.
- Promotion to OB1 is an explicit, future, human-in-the-loop step.
