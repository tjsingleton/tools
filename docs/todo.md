# TODO

## TypeScript (later)

- Support `tools/<name>/main.ts` via a lightweight runner path (likely `npx tsx main.ts`).
- Decide whether TypeScript tools share a top-level `package.json` or stay per-tool.
- Add a `tools/_template_ts/` once the first TS tool lands.

## Agent mode (later)

- Define `agent.yaml` schema (model, system prompt, tools, memory).
- Implement `python scripts/run_tool.py <tool> --agent`:
  - Parse `agent.yaml` (PyYAML extra).
  - Provide a thin adapter for provider/model selection.
  - Keep orchestration in repo; keep “intelligence” outside it.

## Repo hygiene

- Add a `justfile` or `Makefile` only if shortcuts become repetitive.
- Add `results/` conventions if you start saving traces or outputs.

