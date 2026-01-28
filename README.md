# tools

A junk drawer of small experiments.

Core rules:
- One folder = one idea (`tools/<name>/`).
- Each tool is cheap, isolated, and safe to delete.
- The repo provides a thin runner; tools stay self-contained.
- Agent mode is opt-in (scaffolded, not required).

## Layout

```
tools/
  agent/               # optional agent wrapper (thin)
  docs/
    plans/             # design notes
    todo.md            # future work / ideas
  scripts/
    run_tool.py        # entry point
  tools/
    _template/         # copy-paste starter
    <tool-name>/       # one folder = one experiment
```

## Run a tool

Run:

```bash
python scripts/run_tool.py <tool-name> [--] <args...>
```

Examples:

```bash
python scripts/run_tool.py carrier-api
python scripts/run_tool.py carrier-api -- --help
```

If `tools/<tool-name>/main.py` exists, the runner executes it with the tool folder as the working directory.

## Create a tool

Start from the template:

```bash
cp -R tools/_template tools/my-tool
```

Then edit:
- `tools/my-tool/notes.md`
- `tools/my-tool/main.py` (optional)

## TODO

See `docs/todo.md`.
