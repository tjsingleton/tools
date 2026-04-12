from __future__ import annotations

import pytest

from kp.budget import BudgetRouter, BudgetExceeded, estimate_cost_usd


def test_can_spend_within_limits():
    r = BudgetRouter()
    ok, reason = r.can_spend(0.01)
    assert ok
    assert reason == ""


def test_per_item_soft_cap_blocks():
    r = BudgetRouter()
    ok, reason = r.can_spend(0.30)
    assert not ok
    assert "per_item_soft_cap" in reason


def test_halt_blocks():
    r = BudgetRouter(total_spent_usd=4.49)
    ok, reason = r.can_spend(0.10)
    assert not ok
    assert "halt_exceeded" in reason


def test_hard_cap_raises_on_record():
    r = BudgetRouter(total_spent_usd=4.99)
    with pytest.raises(BudgetExceeded):
        r.record(0.10)


def test_estimate_cost_gpt_4o_mini():
    cost = estimate_cost_usd(
        model="openai/gpt-4o-mini",
        input_text="hello world " * 100,
        expected_output_tokens=100,
    )
    assert cost > 0
    assert cost < 0.01
