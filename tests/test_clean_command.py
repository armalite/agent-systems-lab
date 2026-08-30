"""The `clean harness-check` convenience command.

Its safety is structural: it takes no path, resolves the harness-check experiment itself, and
refuses anything not classified `harness_check`. There is deliberately no generic
`clean <experiment>` surface for research evidence to be reachable through.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_lab.cli import app

runner = CliRunner()


def _seed(root: Path) -> Path:
    target = root / "harness_check_001" / "20260830T000000Z"
    (target / "traces").mkdir(parents=True)
    (target / "results.parquet").write_text("x")
    return target


def test_deletes_only_harness_check_output(tmp_path: Path) -> None:
    seeded = _seed(tmp_path)
    other = tmp_path / "calibration_tool_interference_001" / "exec"
    other.mkdir(parents=True)
    (other / "results.parquet").write_text("precious")

    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path), "--yes"]
    )
    assert result.exit_code == 0
    assert not seeded.parent.exists()
    assert (other / "results.parquet").read_text() == "precious"


def test_lists_what_it_will_delete(tmp_path: Path) -> None:
    _seed(tmp_path)
    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path), "--yes"]
    )
    assert "20260830T000000Z" in result.stdout
    assert "Will delete" in result.stdout


def test_requires_confirmation_by_default(tmp_path: Path) -> None:
    seeded = _seed(tmp_path)
    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path)], input="n\n"
    )
    assert result.exit_code == 1
    assert seeded.exists(), "declining the prompt must leave everything in place"


def test_confirmation_accepts_yes(tmp_path: Path) -> None:
    seeded = _seed(tmp_path)
    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path)], input="y\n"
    )
    assert result.exit_code == 0
    assert not seeded.exists()


def test_is_a_no_op_when_there_is_nothing_to_delete(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path), "--yes"]
    )
    assert result.exit_code == 0
    assert "Nothing to delete" in result.stdout


def test_no_generic_result_deletion_surface_exists() -> None:
    """A `clean <anything-else>` must not be reachable."""
    for attempt in (
        ["clean", "smoke-anthropic"],
        ["clean", "calibration"],
        ["clean", "all"],
        ["clean", "results"],
    ):
        assert runner.invoke(app, attempt).exit_code != 0


def test_the_command_takes_no_path_argument(tmp_path: Path) -> None:
    """No caller-supplied path can ever be the deletion target."""
    result = runner.invoke(app, ["clean", "harness-check", str(tmp_path), "--yes"])
    assert result.exit_code != 0


def test_refuses_if_the_experiment_is_not_a_harness_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agent_lab.cli as cli

    config = tmp_path / "experiment.yaml"
    original = Path("experiments/harness_check/experiment.yaml").read_text()
    config.write_text(
        original.replace("classification: harness_check", "classification: calibration")
    )
    for name in ("tasks.yaml", "scripts.yaml"):
        (tmp_path / name).write_text(Path(f"experiments/harness_check/{name}").read_text())
    monkeypatch.setattr(cli, "HARNESS_CHECK_CONFIG", config)

    seeded = _seed(tmp_path)
    result = runner.invoke(
        app, ["clean", "harness-check", "--results-root", str(tmp_path), "--yes"]
    )
    assert result.exit_code == 2
    assert "Refusing" in result.stdout
    assert seeded.exists()
