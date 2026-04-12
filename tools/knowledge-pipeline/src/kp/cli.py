from __future__ import annotations

import json
from pathlib import Path

import click

from kp.events import EventStore
from kp.pipeline.runner import PipelineRunner
from kp.sources.voice_memo import VoiceMemoPlugin


DEFAULT_STAGES = "ingest,normalize,transcribe,analyze,embed,curate"


def _get_plugin(name: str):
    if name == "voice_memo":
        return VoiceMemoPlugin()
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
def run(source: str, path: Path, stages: str, budget_usd: float, dry_run: bool) -> None:
    """Run pipeline stages end-to-end."""
    plugin = _get_plugin(source)
    stage_list = [s.strip() for s in stages.split(",") if s.strip()]
    runner = PipelineRunner(plugin=plugin, dry_run=dry_run, halt_usd=budget_usd)
    summary = runner.run(path=path, stages=stage_list)
    click.echo(json.dumps(summary, indent=2, default=str))


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
