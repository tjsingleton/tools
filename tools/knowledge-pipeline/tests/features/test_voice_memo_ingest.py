from __future__ import annotations

from pathlib import Path

from pytest_bdd import scenarios, given, when, then, parsers

from kp.events import EventStore
from kp.pipeline.stages.ingest import ingest_stage
from kp.sources.voice_memo import VoiceMemoPlugin


scenarios("voice_memo_ingest.feature")


@given("a directory with .m4a and .qta files", target_fixture="audio_dir")
def audio_dir(tmp_path: Path) -> Path:
    (tmp_path / "a.m4a").write_bytes(b"aaa")
    (tmp_path / "b.qta").write_bytes(b"bbb")
    return tmp_path


@given("a previously ingested voice memo", target_fixture="ingested_ctx")
def ingested_ctx(tmp_path: Path) -> dict:
    d = tmp_path / "audio"
    d.mkdir()
    (d / "a.m4a").write_bytes(b"aaa")
    store = EventStore(db_path=tmp_path / "e.db")
    plugin = VoiceMemoPlugin()
    list(ingest_stage(plugin, d, store))
    return {"dir": d, "store": store, "plugin": plugin}


@when("I run discover", target_fixture="discovered")
def run_discover(audio_dir: Path):
    plugin = VoiceMemoPlugin()
    return list(plugin.discover(audio_dir))


@when("I run ingest again", target_fixture="second_run")
def run_ingest_again(ingested_ctx: dict):
    before = sum(1 for _ in ingested_ctx["store"].all())
    result = list(ingest_stage(ingested_ctx["plugin"], ingested_ctx["dir"], ingested_ctx["store"]))
    after = sum(1 for _ in ingested_ctx["store"].all())
    return {"new_items": result, "before": before, "after": after}


@then("all audio files are found")
def all_found(discovered):
    assert len(discovered) == 2


@then("each file has a SHA-256 content hash")
def each_has_hash(discovered):
    for r in discovered:
        assert len(r.content_hash) == 64


@then("no duplicate events are written")
def no_duplicates(second_run):
    assert second_run["new_items"] == []
    assert second_run["before"] == second_run["after"]
