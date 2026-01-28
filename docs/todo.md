# TODO

## TypeScript (later)

- Support `tools/<name>/main.ts` via a lightweight runner path (likely `npx tsx main.ts`).
- Decide whether TypeScript tools share a top-level `package.json` or stay per-tool.
- Add a `tools/_template_ts/` once the first TS tool lands.

## Agent mode (later)

- Implemented MVP `python scripts/run_tool.py <tool> --agent` (OpenAI Responses API).
- Next:
  - Define a richer `agent.yaml` schema (tools, memory, templates).
  - Add a provider abstraction (OpenAI is currently hard-coded).
  - Add streaming and better error reporting.
  - Consider a real YAML parser if config grows beyond the supported subset.

## Repo hygiene

- Add a `justfile` or `Makefile` only if shortcuts become repetitive.
- Add `results/` conventions if you start saving traces or outputs.
