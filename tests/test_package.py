"""Milestone 0 acceptance: the package installs correctly and its entry point is wired up.

These check the *installed distribution* rather than the source tree, because packaging faults
(missing package data, an unregistered console script, a version that drifts from
`pyproject.toml`) only surface after installation.
"""

from importlib.metadata import entry_points, version

import agent_lab


def test_version_is_exposed() -> None:
    assert isinstance(agent_lab.__version__, str)
    assert agent_lab.__version__


def test_installed_distribution_version_matches_package() -> None:
    """Catches `__version__` drifting from the version in `pyproject.toml`."""
    assert version("agent-lab") == agent_lab.__version__


def test_console_script_entry_point_is_registered() -> None:
    """The `agent-lab` command must resolve to the CLI app after installation."""
    scripts = entry_points(group="console_scripts")
    matching = [ep for ep in scripts if ep.name == "agent-lab"]
    assert len(matching) == 1, "expected exactly one `agent-lab` console script"
    assert matching[0].value == "agent_lab.cli:app"
    assert matching[0].load() is not None
