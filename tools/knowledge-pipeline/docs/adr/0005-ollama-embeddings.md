# ADR 0005 — Ollama for embeddings

**Status:** Accepted

## Context
Embeddings could come from openai, voyage, cohere, or a local model.

## Decision
`nomic-embed-text` via local `ollama` (http://localhost:11434).

## Consequences
- $0 marginal cost — keeps embedding out of the budget.
- No data leaves the machine for embedding.
- Requires `ollama serve` running; well-documented in runbooks.
