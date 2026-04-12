# Budget

The pipeline enforces three layers of budget control:

| Layer | Default | Behavior |
|---|---|---|
| Per-item soft cap | $0.25 | Any single estimated call above this is skipped. |
| Halt threshold | $4.50 | If total_spent + estimated > halt, emit `BudgetDeferred`. |
| Hard cap | $5.00 | If total_spent exceeds this, `BudgetExceeded` is raised. |

## Flow

```
estimate_cost_usd(model=..., input_text=doc.text) -> float
BudgetRouter.can_spend(estimate) -> (allowed, reason)
    if not allowed: emit BudgetDeferred, skip
provider.chat(...) -> response
BudgetRouter.record(actual_cost_from_usage_or_estimate)
```

## Pricing
`prices.yaml` contains `$/1M tokens` for each supported model. Override by
passing a different path to `load_prices(path)`.

- `gpt-4o-mini`: $0.15 input / $0.60 output per 1M tokens.
- `nomic-embed-text`: free (local ollama).
