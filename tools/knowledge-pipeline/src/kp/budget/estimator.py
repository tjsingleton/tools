from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_PRICES_PATH = Path(__file__).parent / "prices.yaml"


def load_prices(path: Path | None = None) -> dict[str, Any]:
    p = path or _PRICES_PATH
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _rough_token_count(text: str) -> int:
    # Rough heuristic: ~4 chars/token for English prose.
    return max(1, len(text) // 4)


def estimate_cost_usd(
    *,
    model: str,
    input_text: str = "",
    expected_output_tokens: int = 512,
    prices: dict[str, Any] | None = None,
) -> float:
    prices = prices or load_prices()
    models = prices.get("models", {})
    model_prices = models.get(model) or models.get(model.split("/")[-1]) or {
        "input_per_m": 0.15,
        "output_per_m": 0.60,
    }
    in_tokens = _rough_token_count(input_text)
    out_tokens = expected_output_tokens
    cost = (
        (in_tokens / 1_000_000) * float(model_prices.get("input_per_m", 0.0))
        + (out_tokens / 1_000_000) * float(model_prices.get("output_per_m", 0.0))
    )
    return round(cost, 6)
