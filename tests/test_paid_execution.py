"""Paid-execution safety.

Replaces the Milestone 2 test that asserted no provider SDK was installed. That assertion could
not survive Milestone 3, but its *intent* must: default work is free and offline, spending
requires explicit per-invocation authorization, and budgets are enforced.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from agent_lab.cli import app
from agent_lab.experiments.config import ExperimentConfig, load_experiment
from agent_lab.experiments.runner import build_adapter, run_experiment
from agent_lab.models.provider import (
    PaidExecutionGate,
    PaidExecutionNotAuthorizedError,
    RequestBudgetExceededError,
    redact,
)

SMOKE = Path("experiments/smoke_anthropic/experiment.yaml")
runner = CliRunner()


def _raw() -> dict[str, Any]:
    return yaml.safe_load(SMOKE.read_text())


# ---------------------------------------------------------------- the gate itself


def test_credentials_alone_authorize_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The central rule: a configured key is not authorization (`SPEC.md` s19)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-not-a-real-key")
    gate = PaidExecutionGate(provider="anthropic", authorized=False, max_requests=10)
    with pytest.raises(PaidExecutionNotAuthorizedError, match="not authorized"):
        gate.authorize()


def test_authorization_without_a_budget_is_refused() -> None:
    gate = PaidExecutionGate(provider="anthropic", authorized=True, max_requests=None)
    with pytest.raises(PaidExecutionNotAuthorizedError, match="max_provider_requests"):
        gate.authorize()


def test_budget_is_enforced_per_request() -> None:
    gate = PaidExecutionGate(provider="anthropic", authorized=True, max_requests=2)
    gate.consume()
    gate.consume()
    with pytest.raises(RequestBudgetExceededError, match="budget exhausted"):
        gate.consume()
    assert gate.requests_used == 2


def test_free_providers_are_ungated_and_unmetered() -> None:
    gate = PaidExecutionGate(provider="fake", authorized=False, max_requests=None)
    gate.authorize()
    for _ in range(100):
        gate.consume()
    assert gate.requests_used == 0
    assert gate.is_paid is False


# ---------------------------------------------------------------- wiring


def test_building_a_paid_adapter_without_authorization_fails() -> None:
    """No client is constructed, so no credential is ever read."""
    resolved = load_experiment(SMOKE)
    gate = PaidExecutionGate(provider="anthropic", authorized=False, max_requests=10)
    with pytest.raises(PaidExecutionNotAuthorizedError):
        build_adapter(resolved, gate)


def test_run_experiment_refuses_paid_execution_by_default(tmp_path: Path) -> None:
    resolved = load_experiment(SMOKE)
    with pytest.raises(PaidExecutionNotAuthorizedError):
        asyncio.run(run_experiment(resolved, results_root=tmp_path))


def test_cli_run_refuses_without_allow_paid() -> None:
    result = runner.invoke(app, ["run", str(SMOKE)])
    assert result.exit_code == 2
    assert "--allow-paid" in result.stdout
    assert "PAID PROVIDER RUN" in result.stdout


def test_cli_run_previews_budget_and_controls_before_spending() -> None:
    result = runner.invoke(app, ["run", str(SMOKE)])
    assert "request budget      10" in result.stdout
    assert "claude-opus-5" in result.stdout


# ---------------------------------------------------------------- config guards


def test_paid_provider_requires_declared_cost_controls() -> None:
    raw = _raw()
    del raw["cost_controls"]
    with pytest.raises(ValueError, match="max_provider_requests"):
        ExperimentConfig.model_validate(raw)


def test_paid_provider_rejects_temperature() -> None:
    raw = _raw()
    raw["model"]["parameters"]["temperature"] = 0
    with pytest.raises(ValueError, match="temperature is unsupported"):
        ExperimentConfig.model_validate(raw)


def test_paid_provider_requires_explicit_max_tokens() -> None:
    raw = _raw()
    del raw["model"]["parameters"]["max_tokens"]
    with pytest.raises(ValueError, match="max_tokens must be declared"):
        ExperimentConfig.model_validate(raw)


def test_smoke_experiment_is_classified_as_a_harness_check() -> None:
    """Real-provider smoke validation is not calibration and not Phase 0 (`SPEC.md` M3, v2.3)."""
    assert load_experiment(SMOKE).config.classification == "harness_check"


def test_smoke_experiment_is_small() -> None:
    resolved = load_experiment(SMOKE)
    planned = (
        len(resolved.config.conditions)
        * len(resolved.selected_tasks())
        * resolved.config.repetitions
    )
    assert planned == 3
    assert resolved.config.cost_controls is not None
    assert resolved.config.cost_controls.max_provider_requests <= 10


# ---------------------------------------------------------------- offline guarantee


def test_default_test_run_makes_no_provider_calls(pytestconfig: pytest.Config) -> None:
    """The `paid` marker still gates every billable test path."""
    assert pytestconfig.getini("addopts")
    assert "not paid" in pytestconfig.getini("addopts")


def test_credentials_never_survive_redaction() -> None:
    payload = {"headers": {"x-api-key": "sk-ant-api03-abcdefghijklmnop"}, "list": ["sk-ant-zz"]}
    scrubbed = redact(payload)
    assert "sk-ant" not in str(scrubbed)
