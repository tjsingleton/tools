# ADR 0001 — Live in tools/ subdir, not a separate repo, not in PKB

**Status:** Accepted

## Context
We need a home for the knowledge pipeline. Options:
1. New repo.
2. Inside the personal knowledge base (PKB/OB1).
3. Subdirectory in the existing `tools/` monorepo.

## Decision
(3) — subdirectory at `tools/knowledge-pipeline/`.

## Consequences
- Shares repo infra (CI, hooks, pyproject conventions) with other tools.
- Does not entangle pipeline code with PKB content; PKB stays content-only.
- No cross-repo coordination cost when iterating.
