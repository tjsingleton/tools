# Tools Repo Design

**Date:** 2026-01-28  
**Goal:** Create a lightweight `tools` repo for cheap, isolated experiments.

## Principles

- One folder = one idea.
- No monoliths. No framework by default.
- Tools are safe to delete.
- Agent mode is optional and declared as data.

## Layout

- `tools/<name>/` is the unit of work.
- A tool may contain:
  - `notes.md` (always encouraged)
  - `main.py` (optional runnable entrypoint)
  - `agent.yaml` (optional, later)
  - `index.html` (optional UI, later)

## Running

`scripts/run_tool.py <tool>` runs `tools/<tool>/main.py` with the tool folder as CWD.

## Decisions

- Python first.
- TypeScript later (captured in `docs/todo.md`).
- Agent mode scaffold exists, but stays thin until needed.

