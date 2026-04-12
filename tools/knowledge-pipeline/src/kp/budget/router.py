from __future__ import annotations

from dataclasses import dataclass


HALT_USD = 4.50
HARD_CAP_USD = 5.00
PER_ITEM_SOFT_CAP = 0.25


class BudgetExceeded(Exception):
    """Raised when hard cap is exceeded."""


@dataclass
class BudgetRouter:
    total_spent_usd: float = 0.0
    halt_usd: float = HALT_USD
    hard_cap_usd: float = HARD_CAP_USD
    per_item_soft_cap: float = PER_ITEM_SOFT_CAP

    def can_spend(self, estimated_cost_usd: float) -> tuple[bool, str]:
        """Return (allowed, reason). reason empty when allowed."""
        if self.total_spent_usd > self.hard_cap_usd:
            return False, f"hard_cap_exceeded:{self.total_spent_usd:.4f}>{self.hard_cap_usd}"
        if estimated_cost_usd > self.per_item_soft_cap:
            return False, f"per_item_soft_cap:{estimated_cost_usd:.4f}>{self.per_item_soft_cap}"
        projected = self.total_spent_usd + estimated_cost_usd
        if projected > self.halt_usd:
            return False, f"halt_exceeded:{projected:.4f}>{self.halt_usd}"
        return True, ""

    def record(self, cost_usd: float) -> None:
        self.total_spent_usd = round(self.total_spent_usd + cost_usd, 6)
        if self.total_spent_usd > self.hard_cap_usd:
            raise BudgetExceeded(
                f"Hard cap ${self.hard_cap_usd:.2f} exceeded: ${self.total_spent_usd:.4f}"
            )

    def status(self) -> dict:
        return {
            "total_spent_usd": self.total_spent_usd,
            "halt_usd": self.halt_usd,
            "hard_cap_usd": self.hard_cap_usd,
            "per_item_soft_cap": self.per_item_soft_cap,
            "remaining_to_halt": max(0.0, self.halt_usd - self.total_spent_usd),
        }
