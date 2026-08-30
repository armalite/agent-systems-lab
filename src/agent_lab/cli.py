"""Command-line entry point.

Milestone 2 exposes `validate` and `run` only. `summarize`, `compare`, and `inspect` arrive with
the analysis ergonomics of Milestone 5; persisted traces and results are the source of truth in
the meantime.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from agent_lab import __version__

app = typer.Typer(
    add_completion=False,
    help="Agent Systems Lab - experimental harness for evolving LLM agent systems.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed agent-lab version and exit."),
    ] = False,
) -> None:
    """Agent Systems Lab CLI."""
    if version:
        typer.echo(f"agent-lab {__version__}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def validate(
    config: Annotated[Path, typer.Argument(help="Path to an experiment.yaml")],
) -> None:
    """Resolve an experiment without executing it, and report its fingerprints."""
    from agent_lab.experiments.config import load_experiment

    resolved = load_experiment(config)
    run_count = (
        len(resolved.config.conditions)
        * len(resolved.selected_tasks())
        * resolved.config.repetitions
    )
    typer.echo(f"experiment            {resolved.config.id}")
    typer.echo(f"classification        {resolved.config.classification}")
    typer.echo(
        f"adapter               {resolved.config.adapter.kind} ({resolved.config.model.provider})"
    )
    typer.echo(f"conditions            {', '.join(resolved.config.conditions)}")
    typer.echo(
        f"tasks x repetitions   {len(resolved.selected_tasks())} x {resolved.config.repetitions}"
    )
    typer.echo(f"planned runs          {run_count}")
    typer.echo(f"config fingerprint    {resolved.config_fingerprint}")
    typer.echo(f"task set fingerprint  {resolved.task_set_fingerprint}")
    typer.echo(f"script set fingerprint {resolved.script_set_fingerprint}")
    typer.echo("OK")


@app.command()
def run(
    config: Annotated[Path, typer.Argument(help="Path to an experiment.yaml")],
    results_root: Annotated[
        Path, typer.Option(help="Where execution artifacts are written.")
    ] = Path("results"),
) -> None:
    """Execute an experiment and persist traces, results, and provenance.

    Only the deterministic scripted adapter exists; no provider integration and no paid path.
    """
    from agent_lab.experiments.config import load_experiment
    from agent_lab.experiments.runner import run_experiment

    resolved = load_experiment(config)
    paths, rows = asyncio.run(run_experiment(resolved, results_root=results_root))
    primary = sum(1 for row in rows if row.first_call_routing_correct)
    success = sum(1 for row in rows if row.task_success)
    typer.echo(f"execution   {paths.root}")
    typer.echo(f"runs        {len(rows)}")
    typer.echo(f"primary ok  {primary}/{len(rows)}  (first-call routing)")
    typer.echo(f"task ok     {success}/{len(rows)}")
    typer.echo(f"results     {paths.results}")
    typer.echo(f"traces      {paths.traces}")
