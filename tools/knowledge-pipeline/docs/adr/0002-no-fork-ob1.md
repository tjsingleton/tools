# ADR 0002 — Do not fork OB1; wrap via MCP

**Status:** Accepted

## Context
OB1 is the canonical capture system. The pipeline could either fork OB1 logic,
call its CLI, or use the MCP server contract.

## Decision
Use OB1 **only** via MCP tools. The pipeline keeps a thin `OB1Client` wrapper
that is disabled in MVP (`dry_run=True`).

## Consequences
- Curate writes proposals to `~/Library/KnowledgePipeline/review/` — never mutates OB1.
- Promotion is explicitly human-in-the-loop until the MCP path is exercised.
- OB1 remains the source of truth; the pipeline is strictly upstream.
