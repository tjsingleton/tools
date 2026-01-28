# tools

A junk drawer of small experiments. One folder = one idea.

This repo is intentionally lightweight: every idea is cheap, isolated, and disposable. Any tool can later be upgraded to use an agent without refactoring the rest of the repo.

## Philosophy

- One folder = one idea
- No monoliths, no frameworks by default
- Tools can be static, scripted, or API-backed
- Agent configuration is data, not code
- Everything should be safe to delete

## Repository Layout

```
tools/
  tools/               # one folder = one experiment
    _template/
    <tool-name>/
  scripts/
    run_tool.py         # entry point

  agent/                # optional agent wrapper (thin)
  docs/
    plans/             # design notes
    todo.md            # future work
```

## Tool Folder Contract

Each folder under `tools/` is self-contained.

Minimum viable tool:

```
tools/my-idea/
  notes.md
```

Common additions:

- `main.py` — scripts, API poking, etc.
- `agent.yaml` — opt-in agent behavior (future work; scaffold exists)
- `index.html` — single-file UI (optional)
- `notes.md` — findings, assumptions, links

No tool is required to use an agent.

## Running a Tool

Run:

```bash
python scripts/run_tool.py <tool-name> [--] <args...>
```

What happens:

- Loads `tools/<tool-name>/`
- If `main.py` exists, runs it with the tool folder as CWD
- Otherwise prints a helpful message pointing to `notes.md`

## Creating a Tool

Start from the template:

```bash
cp -R tools/_template tools/my-tool
```

Then edit:
- `tools/my-tool/notes.md`
- `tools/my-tool/main.py` (optional)

## Agent Mode (Optional)

There is a thin scaffold in `agent/`. Agent mode is intentionally not implemented yet; see `docs/todo.md` for the planned shape.

## TODO / Future Work

See `docs/todo.md`.
