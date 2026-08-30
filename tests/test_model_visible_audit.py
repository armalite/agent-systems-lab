"""Audit what actually reaches the model, and prove no paid path exists.

Observation O-001's follow-up: the surface an author reviews in code is not the surface the
model receives. M1 audited the MCP boundary; this audits the **adapter** boundary, using the
rendered tools preserved in the trace rather than the source.
"""

import json
from pathlib import Path

import pytest

from agent_lab.tracing import events as ev
from agent_lab.tracing.recorder import read_trace
from tests.harness import Execution, execute
from tests.test_mcp_server import DESIGN_VOCABULARY

CONDITION_LABELS = ("customer_baseline_v1", "customer_overlap_v1")


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    return execute(tmp_path_factory.mktemp("audit"))


def _model_requests(traces: Path):  # type: ignore[no-untyped-def]
    for path in traces.glob("*.jsonl"):
        for event in read_trace(path):
            if event.event_type == ev.MODEL_REQUEST:
                yield event


def test_rendered_tools_carry_no_design_vocabulary(execution: Execution) -> None:
    paths, _ = execution
    for event in _model_requests(paths.traces):
        blob = json.dumps(event.payload["rendered_tools"]).casefold()
        for leaked in DESIGN_VOCABULARY:
            assert leaked not in blob, f"{leaked!r} reached the model in {event.run_id}"


def test_system_instructions_carry_no_design_vocabulary(execution: Execution) -> None:
    paths, _ = execution
    for event in _model_requests(paths.traces):
        blob = str(event.payload["system_instructions"]).casefold()
        for leaked in DESIGN_VOCABULARY:
            assert leaked not in blob


def test_condition_identifiers_never_reach_the_model(execution: Execution) -> None:
    """Tool-space ids are internal condition labels, not model-visible context."""
    paths, _ = execution
    for event in _model_requests(paths.traces):
        blob = json.dumps(
            {
                "system": event.payload["system_instructions"],
                "tools": event.payload["rendered_tools"],
                "messages": event.payload["messages"],
            }
        ).casefold()
        for label in CONDITION_LABELS:
            assert label not in blob


def test_server_identity_is_recorded_but_not_presented_to_the_model(execution: Execution) -> None:
    """The v2.2 distinction, verified against evidence rather than intent."""
    paths, _ = execution
    for path in list(paths.traces.glob("*.jsonl"))[:4]:
        events = read_trace(path)
        connected = next(e for e in events if e.event_type == ev.ENVIRONMENT_CONNECTED)
        server_name = connected.payload["descriptor"]["server"]["name"]
        assert server_name  # the harness observed it
        for event in events:
            if event.event_type != ev.MODEL_REQUEST:
                continue
            presented = json.dumps(
                [event.payload["rendered_tools"], event.payload["system_instructions"]]
            )
            assert server_name not in presented


def test_model_surface_fingerprint_is_recorded_on_every_event(execution: Execution) -> None:
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        for event in read_trace(path):
            assert event.model_surface_fingerprint.startswith("fp1:sha256:")
            assert event.environment_fingerprint.startswith("fp1:sha256:")
            assert event.model_surface_fingerprint != event.environment_fingerprint


def test_no_provider_sdk_is_declared_or_importable() -> None:
    """Milestone 2 has no provider integration and no paid execution path at all."""
    pyproject = Path("pyproject.toml").read_text().casefold()
    dependencies = pyproject.split("[project.scripts]")[0]
    for banned in ("anthropic", "openai", "litellm", "langchain"):
        assert banned not in dependencies

    for module in ("anthropic", "openai"):
        with pytest.raises(ImportError):
            __import__(module)


def test_runner_rejects_a_non_scripted_adapter() -> None:
    """A provider adapter cannot be reached even if a config asks for one."""
    import yaml

    from agent_lab.experiments.config import ExperimentConfig

    raw = yaml.safe_load(Path("experiments/harness_check/experiment.yaml").read_text())
    raw["adapter"]["kind"] = "anthropic"
    with pytest.raises(ValueError):
        ExperimentConfig.model_validate(raw)
