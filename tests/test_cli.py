"""Milestone 0 acceptance: the `agent-lab` console script is wired up correctly."""

from typer.testing import CliRunner

from agent_lab import __version__
from agent_lab.cli import app

runner = CliRunner()


def test_version_flag_reports_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_bare_invocation_succeeds() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
