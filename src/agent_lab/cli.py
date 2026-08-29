"""Command-line entry point.

Milestone 0 deliberately exposes only `--version`. Experiment commands (`list`, `validate`,
`run`, `summarize`) arrive with the milestones that implement the machinery behind them;
stubbing them early would misrepresent what the lab can currently do.
"""

import typer

from agent_lab import __version__

app = typer.Typer(
    add_completion=False,
    help="Agent Systems Lab - experimental harness for evolving LLM agent systems.",
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed agent-lab version and exit.",
    ),
) -> None:
    """Agent Systems Lab CLI."""
    if version:
        typer.echo(f"agent-lab {__version__}")
        raise typer.Exit(0)
