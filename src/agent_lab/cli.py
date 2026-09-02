"""Command-line entry point.

Exposes `validate`, `run`, and `clean harness-check`. Analysis ergonomics (`summarize`,
`compare`, `inspect`) are a deferred backlog rather than a scheduled milestone (`SPEC.md` s23):
persisted traces and results are the source of truth, and DuckDB queries them directly.
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
    if resolved.memory is not None:
        # Resolved here too, so the exact model-visible memory can be inspected before any run.
        from agent_lab.memory.resolve import resolve_memory

        resolved_memory = resolve_memory(resolved.memory)
        typer.echo(f"memory corpus         {resolved.memory.descriptor.id}")
        typer.echo(f"memory policy         {resolved.memory.policy.id}")
        typer.echo(f"memory presentation   {resolved.memory.presentation.id}")
        typer.echo(
            f"memory entries        {resolved_memory.surface.entry_count} active "
            f"of {len(resolved.memory.descriptor.entries)} declared"
        )
        typer.echo(f"memory descriptor fp  {resolved.memory.descriptor_fingerprint()}")
        typer.echo(f"memory policy fp      {resolved.memory.policy_fingerprint()}")
        typer.echo(f"memory surface fp     {resolved_memory.surface.fingerprint()}")
    typer.echo("OK")


@app.command()
def run(
    config: Annotated[Path, typer.Argument(help="Path to an experiment.yaml")],
    results_root: Annotated[
        Path, typer.Option(help="Where execution artifacts are written.")
    ] = Path("results"),
    allow_paid: Annotated[
        bool,
        typer.Option(
            "--allow-paid",
            help="Authorize cost-incurring provider calls for THIS invocation only.",
        ),
    ] = False,
) -> None:
    """Execute an experiment and persist traces, results, and provenance.

    Cost-incurring providers require `--allow-paid` every time. Having credentials configured
    authorizes nothing on its own.
    """
    from agent_lab.experiments.config import load_experiment
    from agent_lab.experiments.runner import run_experiment

    resolved = load_experiment(config)
    planned = (
        len(resolved.config.conditions)
        * len(resolved.selected_tasks())
        * resolved.config.repetitions
    )
    if resolved.config.can_incur_cost:
        budget = (
            resolved.config.cost_controls.max_provider_requests
            if resolved.config.cost_controls
            else 0
        )
        typer.echo("PAID PROVIDER RUN")
        typer.echo(
            f"  provider/model      {resolved.config.model.provider} / {resolved.config.model.name}"
        )
        typer.echo(f"  controls            {resolved.config.model.parameters}")
        typer.echo(f"  planned runs        {planned}")
        typer.echo(f"  request budget      {budget} (hard ceiling, enforced per request)")
        if not allow_paid:
            typer.echo("")
            typer.echo("Refusing to run: pass --allow-paid to authorize this invocation.")
            raise typer.Exit(2)

    paths, rows = asyncio.run(
        run_experiment(resolved, results_root=results_root, allow_paid=allow_paid)
    )
    primary = sum(1 for row in rows if row.first_call_routing_correct)
    success = sum(1 for row in rows if row.task_success)
    typer.echo(f"execution   {paths.root}")
    typer.echo(f"runs        {len(rows)}")
    typer.echo(f"primary ok  {primary}/{len(rows)}  (first-call routing)")
    typer.echo(f"task ok     {success}/{len(rows)}")
    typer.echo(f"results     {paths.results}")
    typer.echo(f"traces      {paths.traces}")


clean_app = typer.Typer(
    help="Delete disposable harness output. Deliberately offers no generic result deletion."
)
app.add_typer(clean_app, name="clean")

HARNESS_CHECK_CONFIG = Path("experiments/harness_check/experiment.yaml")
HARNESS_CHECK_CLASSIFICATION = "harness_check"


@clean_app.command("harness-check")
def clean_harness_check(
    results_root: Annotated[Path, typer.Option(help="Where execution artifacts live.")] = Path(
        "results"
    ),
    yes: Annotated[bool, typer.Option("--yes", help="Skip the confirmation prompt.")] = False,
) -> None:
    """Delete harness-check executions only.

    Takes no path argument by design. It resolves the harness-check experiment, refuses to
    proceed unless that experiment is classified `harness_check`, and deletes only that
    experiment's output. Real research evidence is never reachable from this command, and there
    is deliberately no generic `clean <experiment>` surface.
    """
    import shutil

    from agent_lab.experiments.config import load_experiment

    resolved = load_experiment(HARNESS_CHECK_CONFIG)
    if resolved.config.classification != HARNESS_CHECK_CLASSIFICATION:
        typer.echo(
            f"Refusing: {HARNESS_CHECK_CONFIG} is classified "
            f"{resolved.config.classification!r}, not {HARNESS_CHECK_CLASSIFICATION!r}."
        )
        raise typer.Exit(2)

    target = results_root / resolved.config.id
    if not target.exists():
        typer.echo(f"Nothing to delete: {target} does not exist.")
        raise typer.Exit(0)

    executions = sorted(path.name for path in target.iterdir() if path.is_dir())
    typer.echo(f"Will delete {target} ({len(executions)} execution(s)):")
    for name in executions:
        typer.echo(f"  {name}")
    if not yes and not typer.confirm("Delete this harness-check output?"):
        typer.echo("Aborted.")
        raise typer.Exit(1)

    shutil.rmtree(target)
    typer.echo(f"Deleted {target}")
