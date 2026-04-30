from __future__ import annotations

import json
from pathlib import Path

import click

from kp.events import EventStore
from kp.pipeline.runner import PipelineRunner
from kp.sources.voice_memo import VoiceMemoPlugin


DEFAULT_STAGES = "ingest,normalize,transcribe,diarize,analyze"


def _get_plugin(name: str):
    if name == "voice_memo":
        return VoiceMemoPlugin()
    if name == "polished_memo":
        from kp.sources.polished_memo import PolishedMemoPlugin

        return PolishedMemoPlugin()
    raise click.ClickException(f"Unknown source: {name}")


@click.group()
def cli() -> None:
    """Knowledge pipeline CLI."""


@cli.command()
@click.option("--source", required=True)
@click.option("--path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run/--no-dry-run", default=True)
def ingest(source: str, path: Path, dry_run: bool) -> None:
    """Discover and ingest items from a source."""
    plugin = _get_plugin(source)
    runner = PipelineRunner(plugin=plugin, dry_run=dry_run)
    summary = runner.run(path=path, stages=["ingest"])
    click.echo(json.dumps(summary, indent=2, default=str))


@cli.command()
@click.option("--source", required=True)
@click.option("--path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--stages", default=DEFAULT_STAGES)
@click.option("--budget-usd", default=4.50, type=float)
@click.option("--dry-run/--no-dry-run", default=True)
@click.option(
    "--reprocess",
    is_flag=True,
    default=False,
    help="Backfill later stages from already-ingested items (skips ingest+normalize).",
)
@click.option(
    "--whisper-model",
    default="small",
    show_default=True,
    help="faster-whisper model size: tiny|base|small|medium|large-v3.",
)
def run(
    source: str,
    path: Path,
    stages: str,
    budget_usd: float,
    dry_run: bool,
    reprocess: bool,
    whisper_model: str,
) -> None:
    """Run pipeline stages end-to-end."""
    plugin = _get_plugin(source)
    stage_list = [s.strip() for s in stages.split(",") if s.strip()]
    runner = PipelineRunner(
        plugin=plugin,
        dry_run=dry_run,
        halt_usd=budget_usd,
        whisper_model=whisper_model,
    )
    summary = runner.run(path=path, stages=stage_list, reprocess=reprocess)
    click.echo(json.dumps(summary, indent=2, default=str))


@cli.command()
@click.option("--port", default=8765, type=int, show_default=True)
@click.option("--host", default="127.0.0.1", show_default=True)
def serve(port: int, host: str) -> None:
    """Start the read-only review web UI."""
    from kp.web.app import run_server

    run_server(host=host, port=port)


VOICE_MEMOS_APP_DIR = Path.home() / "Library" / "Group Containers" / "group.com.apple.VoiceMemos.shared" / "Recordings"
DEFAULT_DUMP_DIR = Path("/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP")


@cli.command()
@click.option(
    "--source-dir",
    default=str(VOICE_MEMOS_APP_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--dest",
    default=str(DEFAULT_DUMP_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
)
def fetch(source_dir: Path, dest: Path) -> None:
    """Copy new audio from the Voice Memos.app dir to the dump (idempotent via SHA-256)."""
    from kp.sources.voice_memo.fetch import fetch_voice_memos

    summary = fetch_voice_memos(source_dir=Path(source_dir), dest=Path(dest))
    click.echo(json.dumps(summary, indent=2, default=str))


AUDIO_CACHE_DIR = Path.home() / "Library" / "KnowledgePipeline" / "cache" / "audio"


@cli.command()
@click.option("--short-id", "short_id_arg", default=None, help="Short id like kp-XXXXXXXX")
@click.option("--hash", "content_hash", default=None, help="Full content hash")
@click.option("--dry-run/--no-dry-run", default=True)
def purge(short_id_arg: str | None, content_hash: str | None, dry_run: bool) -> None:
    """Purge a memo: source file + sibling .vtt/.srt + cached .m4a + all events."""
    from kp.web._data import short_id as compute_short_id

    if not short_id_arg and not content_hash:
        raise click.UsageError("Provide --short-id or --hash")

    store = EventStore()

    if short_id_arg and not content_hash:
        seen: set[str] = set()
        match: str | None = None
        for r in store.all():
            h = r["content_hash"]
            if h in seen:
                continue
            seen.add(h)
            if compute_short_id(h) == short_id_arg:
                match = h
                break
        if not match:
            raise click.ClickException(f"No memo with short_id {short_id_arg}")
        content_hash = match

    rows = store.by_hash(content_hash)
    if not rows:
        raise click.ClickException(f"No events for hash {content_hash}")

    files: list[Path] = []
    for r in rows:
        if r["event_type"] == "ItemIngested":
            data = json.loads(r["data_json"])
            p = data.get("path")
            if not p:
                continue
            src = Path(p)
            files.append(src)
            for ext in (".vtt", ".srt"):
                sib = src.with_suffix(ext)
                if sib.exists():
                    files.append(sib)

    cached = AUDIO_CACHE_DIR / f"{content_hash}.m4a"
    if cached.exists():
        files.append(cached)

    deleted_files: list[str] = []
    missing_files: list[str] = []
    if not dry_run:
        for f in files:
            try:
                f.unlink()
                deleted_files.append(str(f))
            except FileNotFoundError:
                missing_files.append(str(f))
        events_deleted = store.delete_by_hash(content_hash)
    else:
        events_deleted = len(rows)

    summary = {
        "content_hash": content_hash,
        "short_id": compute_short_id(content_hash),
        "files_targeted": [str(f) for f in files],
        "files_deleted": deleted_files,
        "files_missing": missing_files,
        "events_deleted": events_deleted,
        "dry_run": dry_run,
    }
    click.echo(json.dumps(summary, indent=2))


@cli.group("voice-memo")
def voice_memo() -> None:
    """Voice memo commands."""


@voice_memo.command("backfill-fingerprints")
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    show_default=True,
    help="Report what would be emitted without writing events.",
)
def backfill_fingerprints(dry_run: bool) -> None:
    """Fingerprint all existing voice_memo entries and emit AudioFingerprinted events.

    Idempotent: entries that already have an AudioFingerprinted event are skipped.
    After processing, prints a duplicate-cluster report. No auto-merge.
    """
    import datetime

    from kp.events import AudioFingerprinted, EventStore
    from kp.sources.voice_memo.fingerprint import (
        FingerprintFailed,
        FingerprintUnavailable,
        cluster_by_fingerprint,
        fingerprint_file,
    )

    store = EventStore()

    # All distinct voice_memo ItemIngested events (ordered ASC by id)
    ingested_events = store.query(event_type="ItemIngested", source="voice_memo")
    seen_hashes: set[str] = set()
    candidates: list[dict] = []
    for evt in ingested_events:
        ch = evt["content_hash"]
        if ch not in seen_hashes:
            seen_hashes.add(ch)
            candidates.append(evt)

    # Build set of already-fingerprinted hashes (idempotency guard)
    already_fp: set[str] = {
        evt["content_hash"] for evt in store.query(event_type="AudioFingerprinted")
    }

    stats: dict = {
        "candidates": len(candidates),
        "skipped_already_fingerprinted": 0,
        "skipped_missing_path": 0,
        "skipped_fingerprint_failed": 0,
        "emitted": 0,
        "clusters_with_duplicates": 0,
        "dry_run": dry_run,
    }

    new_fps: list[tuple[str, str]] = []  # (content_hash, fp) computed this run

    for evt in candidates:
        ch = evt["content_hash"]

        if ch in already_fp:
            stats["skipped_already_fingerprinted"] += 1
            continue

        # Resolve audio path: prefer latest ItemNormalized data.audio_path
        audio_path: str | None = None
        for row in reversed(store.by_hash(ch)):
            if row.get("event_type") == "ItemNormalized":
                data = json.loads(row["data_json"])
                p = data.get("audio_path")
                if p:
                    audio_path = p
                    break

        # Fall back to ItemIngested data.path
        if not audio_path:
            audio_path = evt["data"].get("path")

        if not audio_path or not Path(audio_path).exists():
            click.echo(
                f"WARNING: skipping {ch[:8]}... — no audio file at {audio_path!r}",
                err=True,
            )
            stats["skipped_missing_path"] += 1
            continue

        # Compute fingerprint
        try:
            duration, fp = fingerprint_file(Path(audio_path))
        except FingerprintUnavailable as exc:
            raise click.ClickException(
                f"fpcalc binary not available — install with `brew install chromaprint`: {exc}"
            )
        except FingerprintFailed as exc:
            click.echo(f"WARNING: fingerprint failed for {ch[:8]}...: {exc}", err=True)
            stats["skipped_fingerprint_failed"] += 1
            continue

        new_fps.append((ch, fp))
        stats["emitted"] += 1

        if not dry_run:
            store.append(
                AudioFingerprinted(
                    content_hash=ch,
                    data={
                        "audio_fingerprint": fp,
                        "audio_duration": duration,
                        "audio_path": audio_path,
                        "computed_by": "backfill",
                    },
                )
            )

    # Cluster report: existing AudioFingerprinted events + new ones (dry-run: not written)
    existing_fp_events = store.query(event_type="AudioFingerprinted")
    all_fp_pairs: list[tuple[str, str]] = [
        (evt["content_hash"], evt["data"]["audio_fingerprint"])
        for evt in existing_fp_events
    ]
    if dry_run:
        all_fp_pairs.extend(new_fps)

    clusters = cluster_by_fingerprint(all_fp_pairs)
    dup_clusters = {fp: hashes for fp, hashes in clusters.items() if len(hashes) >= 2}
    stats["clusters_with_duplicates"] = len(dup_clusters)

    click.echo(json.dumps(stats, indent=2))

    if dup_clusters:
        ingested_map = {evt["content_hash"]: evt for evt in ingested_events}
        cluster_report = []
        for fp_str, hashes in dup_clusters.items():
            members = []
            for h in hashes:
                p = ingested_map.get(h, {}).get("data", {}).get("path", "")
                members.append({"content_hash": h, "basename": Path(p).name if p else ""})
            cluster_report.append(
                {"fingerprint_prefix": fp_str[:16] + "...", "members": members}
            )

        click.echo("\nclusters:")
        click.echo(json.dumps(cluster_report, indent=2))

        today = datetime.date.today().isoformat()
        spike_dir = Path(".omc/spikes")
        spike_dir.mkdir(parents=True, exist_ok=True)
        report_path = spike_dir / f"fingerprint-clusters-{today}.json"
        report_path.write_text(
            json.dumps(
                {"dry_run": dry_run, "stats": stats, "clusters": cluster_report},
                indent=2,
            )
        )
        click.echo(f"\nReport written to {report_path}", err=True)


@cli.group()
def events() -> None:
    """Event log commands."""


@events.command("tail")
@click.option("--source", default=None)
@click.option("--limit", default=50, type=int)
def events_tail(source: str | None, limit: int) -> None:
    store = EventStore()
    for row in store.tail(source=source, limit=limit):
        click.echo(json.dumps(row, default=str))


@cli.group()
def curate() -> None:
    """Curation commands."""


@curate.command("review")
def curate_review() -> None:
    """Show pending review items."""
    review_dir = Path.home() / "Library" / "KnowledgePipeline" / "review"
    if not review_dir.exists():
        click.echo("(no review directory yet)")
        return
    files = sorted(review_dir.glob("*.json"))
    if not files:
        click.echo("(no pending review items)")
        return
    for f in files:
        click.echo(f"=== {f.name} ===")
        click.echo(f.read_text())


@cli.group()
def budget() -> None:
    """Budget commands."""


@budget.command("status")
def budget_status() -> None:
    from kp.budget import BudgetRouter

    click.echo(json.dumps(BudgetRouter().status(), indent=2))


if __name__ == "__main__":
    cli()
