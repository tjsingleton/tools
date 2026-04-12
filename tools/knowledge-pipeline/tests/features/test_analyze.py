from __future__ import annotations

from pytest_bdd import scenarios, given, when, then

from kp.budget import BudgetRouter
from kp.events import EventStore
from kp.pipeline.plugin import Document
from kp.pipeline.stages.analyze import analyze_stage


scenarios("analyze.feature")


@given("a document and a budget router at halt threshold", target_fixture="ctx")
def ctx(tmp_path):
    store = EventStore(db_path=tmp_path / "e.db")
    # Already over halt; any spend must defer.
    budget = BudgetRouter(total_spent_usd=4.50)
    doc = Document(
        content_hash="h",
        source="voice_memo",
        text="This is a meaningful transcript about a decision.",
        metadata={},
    )
    return {"store": store, "budget": budget, "doc": doc}


@when("I run analyze", target_fixture="run_result")
def run_analyze(ctx):
    result = analyze_stage(ctx["doc"], store=ctx["store"], budget=ctx["budget"])
    return {"analysis": result, "store": ctx["store"]}


@then("a BudgetDeferred event is written")
def budget_deferred(run_result):
    rows = list(run_result["store"].all())
    assert any(r["event_type"] == "BudgetDeferred" for r in rows)


@then("no AnalysisCompleted event is written")
def no_analysis(run_result):
    rows = list(run_result["store"].all())
    assert not any(r["event_type"] == "AnalysisCompleted" for r in rows)
