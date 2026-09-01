"""The whole M3 path, offline: real runner, real MCP, fake Anthropic client.

This proves the runner is genuinely unchanged by the provider swap, and audits the *persisted*
provider request rather than the code that builds it (Observations O-001 and O-002).
"""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest

import agent_lab.experiments.runner as runner_module
from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.config import ResolvedExperiment, load_experiment
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, derive_result
from agent_lab.experiments.runner import ExecutionPaths, run_experiment
from agent_lab.models.anthropic import AnthropicAdapter
from agent_lab.models.provider import PaidExecutionGate
from agent_lab.tracing import events as ev
from agent_lab.tracing.events import TraceEvent
from agent_lab.tracing.recorder import read_trace
from tests.anthropic_doubles import build_message, text_block, thinking_block
from tests.harness import Execution
from tests.test_mcp_server import DESIGN_VOCABULARY

SMOKE = Path("experiments/smoke_anthropic/experiment.yaml")

ANSWERS = {
    "get_customer": "The email address for customer C102 is priya.r@example.test.",
    "get_order": "Order O204 currently has the status pending.",
    "get_employee": "Employee E104 is assigned to the Porto Alegre office.",
}
CALLS = {
    "sm_001_customer_email": ("get_customer", {"customer_id": "C102"}),
    "sm_002_order_status": ("get_order", {"order_id": "O204"}),
    "sm_003_employee_office": ("get_employee", {"employee_id": "E104"}),
}


class _ScriptedFakeClient:
    """Answers like a well-behaved model: one tool call, then a text answer.

    Emits a thinking block on the tool turn so verbatim continuation replay is exercised on the
    real runner path, not just in adapter unit tests.
    """

    def __init__(self) -> None:
        self.messages = self
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        from tests.anthropic_doubles import tool_use_block

        conversation = kwargs["messages"]
        prompt = str(conversation[0]["content"])
        task_id = next(
            task_id for task_id, (_, args) in CALLS.items() if next(iter(args.values())) in prompt
        )
        tool_name, arguments = CALLS[task_id]
        already_called = any(message["role"] == "assistant" for message in conversation)
        if not already_called:
            return build_message(
                blocks=[
                    thinking_block(f"considering {tool_name}"),
                    tool_use_block("toolu_" + task_id[:6], tool_name, arguments),
                ],
                stop_reason="tool_use",
            )
        return build_message(blocks=[text_block(ANSWERS[tool_name])], stop_reason="end_turn")


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    """Run the real harness end to end with a fake Anthropic client.

    The double is injected through the adapter's public constructor, so the runner, the real MCP
    environment, tracing, derivation, and persistence are all exercised for real - only the
    network call is replaced.
    """
    client = _ScriptedFakeClient()
    resolved = load_experiment(SMOKE)

    def _fake_adapter(_resolved: ResolvedExperiment, gate: PaidExecutionGate) -> AnthropicAdapter:
        gate.authorize()
        return AnthropicAdapter(
            model=resolved.config.model.name,
            parameters=dict(resolved.config.model.parameters),
            gate=gate,
            client=cast(Any, client),
        )

    original = runner_module.build_adapter
    runner_module.build_adapter = _fake_adapter
    try:
        return asyncio.run(
            run_experiment(
                resolved, results_root=tmp_path_factory.mktemp("provider"), allow_paid=True
            )
        )
    finally:
        runner_module.build_adapter = original


def test_all_three_tasks_run_through_the_unchanged_loop(execution: Execution) -> None:
    paths, rows = execution
    assert len(rows) == 3
    assert len(list(paths.traces.glob("*.jsonl"))) == 3
    assert all(row.provider == "anthropic" for row in rows)
    assert all(row.task_success for row in rows)
    assert all(row.first_call_routing_correct for row in rows)


def test_provider_surface_event_is_recorded(execution: Execution) -> None:
    paths, _ = execution
    events = read_trace(next(iter(paths.traces.glob("*.jsonl"))))
    prepared = next(e for e in events if e.event_type == ev.PROVIDER_SURFACE_PREPARED)
    assert prepared.layer == "provider"
    assert prepared.payload["provider_surface_fingerprint"].startswith("fp1:sha256:")
    assert "output_schema" in prepared.payload["dropped_from_model_surface"]


def test_three_fingerprints_are_distinct(execution: Execution) -> None:
    """Environment, model surface, and provider surface are separate objects (`SPEC.md` s9.2)."""
    _, rows = execution
    row = rows[0]
    assert row.environment_fingerprint != row.model_surface_fingerprint
    assert row.model_surface_fingerprint != row.provider_surface_fingerprint
    assert row.environment_fingerprint != row.provider_surface_fingerprint
    assert row.provider_surface_fingerprint.startswith("fp1:sha256:")


def test_exact_full_request_is_persisted_for_every_turn(execution: Execution) -> None:
    """Evidence, not a comparison aid: it includes the messages actually sent."""
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        requests = [e for e in read_trace(path) if e.event_type == ev.MODEL_REQUEST]
        assert len(requests) == 2, "expected a tool turn and an answer turn"
        hashes: set[str] = set()
        for event in requests:
            body = event.payload["provider_request"]
            assert set(body) >= {"model", "system", "tools", "messages", "max_tokens", "thinking"}
            assert body["model"] == "claude-opus-5"
            assert "temperature" not in body
            hashes.add(event.payload["provider_request_hash"])
        assert len(hashes) == 2, "each turn's exact request must hash differently"


def test_thinking_blocks_are_replayed_verbatim_in_the_second_request(execution: Execution) -> None:
    paths, _ = execution
    events = read_trace(next(iter(paths.traces.glob("*.jsonl"))))
    responses = [e for e in events if e.event_type == ev.MODEL_RESPONSE]
    emitted = responses[0].payload["provider_blocks"]
    assert [block["type"] for block in emitted] == ["thinking", "tool_use"]

    second_request = [e for e in events if e.event_type == ev.MODEL_REQUEST][1]
    replayed = second_request.payload["provider_request"]["messages"][1]
    assert replayed["role"] == "assistant"
    assert replayed["content"] == emitted


def test_tool_results_are_sent_back_as_anthropic_tool_result_blocks(execution: Execution) -> None:
    paths, _ = execution
    events = read_trace(next(iter(paths.traces.glob("*.jsonl"))))
    second_request = [e for e in events if e.event_type == ev.MODEL_REQUEST][1]
    tool_message = second_request.payload["provider_request"]["messages"][2]
    assert tool_message["role"] == "user"
    block = tool_message["content"][0]
    assert block["type"] == "tool_result"
    assert block["tool_use_id"].startswith("toolu_")
    assert block["is_error"] is False


def test_provider_response_information_is_preserved(execution: Execution) -> None:
    _, rows = execution
    row = rows[0]
    assert row.model_requested == "claude-opus-5"
    assert row.model_served == "claude-opus-5-served"
    assert row.model_snapshot_available is False
    assert row.provider_stop_reason == "end_turn"
    assert row.provider_request_ids
    assert row.input_tokens is not None and row.input_tokens > 0
    assert json.loads(row.model_controls)["thinking"] == {"type": "adaptive"}


def test_results_still_re_derive_from_the_persisted_traces(execution: Execution) -> None:
    """The M2 guarantee must survive the provider swap."""
    _, rows = execution
    resolved = load_experiment(SMOKE)
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    for row in rows:
        rederived = derive_result(
            events=read_trace(Path(row.trace_path)),
            task=resolved.task_set.by_id(row.task_id),
            resolved=resolved,
            metric_set=metric_set,
            trace_path=Path(row.trace_path),
        )
        assert rederived == row


def test_schema_versions_are_stamped(execution: Execution) -> None:
    paths, rows = execution
    assert all(row.result_schema_version == RESULT_SCHEMA_VERSION == "1.2.0" for row in rows)
    assert all(row.trace_schema_version == "1.2.0" for row in rows)
    manifest = json.loads(paths.manifest.read_text())
    assert manifest["adapter_kind"] == "anthropic"
    assert manifest["paid_execution_authorized"] is True
    assert manifest["provider_requests_used"] == 6
    assert manifest["provider_request_budget"] == 10
    assert manifest["model_snapshot_available"] is False


# ------------------------------------------------------------------ leakage audit


def _provider_requests(paths: ExecutionPaths) -> Iterator[tuple[TraceEvent, str]]:
    for path in paths.traces.glob("*.jsonl"):
        for event in read_trace(path):
            if event.event_type == ev.MODEL_REQUEST:
                yield event, json.dumps(event.payload["provider_request"])


def test_no_design_vocabulary_reaches_the_provider(execution: Execution) -> None:
    paths, _ = execution
    for event, body in _provider_requests(paths):
        lowered = body.casefold()
        for leaked in DESIGN_VOCABULARY:
            assert leaked not in lowered, f"{leaked!r} reached the provider in {event.run_id}"


def test_no_harness_identifiers_reach_the_provider(execution: Execution) -> None:
    """Condition ids, run ids, execution ids, and paths are all harness-internal."""
    paths, rows = execution
    identifiers = {
        rows[0].tool_space_id,
        rows[0].execution_id,
        rows[0].experiment_id,
        str(paths.root),
        "customer_baseline_v1",
        "customer_overlap_v1",
    }
    for event, body in _provider_requests(paths):
        for identifier in identifiers:
            assert identifier not in body, f"{identifier!r} leaked in {event.run_id}"
        assert event.run_id not in body
        assert "results/" not in body


def test_no_credential_shaped_string_is_persisted(execution: Execution) -> None:
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        assert "sk-ant" not in path.read_text()
    assert "sk-ant" not in paths.manifest.read_text()
    assert "sk-ant" not in paths.results.read_bytes().decode("utf-8", errors="ignore")


def test_server_identity_does_not_reach_the_provider(execution: Execution) -> None:
    paths, _ = execution
    descriptor = json.loads((paths.environments / "customer_baseline_v1.json").read_text())
    server_name = descriptor["descriptor"]["server"]["name"]
    assert server_name == "customer-directory"
    for _, body in _provider_requests(paths):
        assert server_name not in body
