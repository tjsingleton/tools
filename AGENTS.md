# Agent Instructions (tools repo)

## Workflow

- Always work on a feature branch.
- Never push directly to `main`.
- Open a PR for every change.

Branch naming:
- `chore/<topic>`, `feat/<topic>`, `fix/<topic>`, `docs/<topic>`

PR expectations:
- Small, focused diffs.
- Include how to verify (commands + expected result).

## Repo Contract

- One folder = one idea under `tools/`.
- Tools are cheap, isolated, and safe to delete.
- Prefer stdlib-only Python unless a dependency is clearly justified.

## Verification

Run before opening a PR:

```bash
python -m compileall -q .
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/run_tool.py --list
```

## Notes

- Secrets stay out of git (`.env` is ignored). Use `.env.example` for documentation.

