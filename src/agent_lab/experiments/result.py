"""Normalized result rows, derived from the raw trace.

`derive_result` reads **only** trace events. It deliberately ignores `EVALUATION_COMPLETED`, so
re-deriving a row from a persisted trace is not circular and can be asserted equal to what was
originally written. That test is what makes "the raw trace is authoritative" (`SPEC.md` s18) a
property of the system rather than a statement of intent.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from agent_lab.environments.surface import canonical_json
from agent_lab.evals.answers import evaluate_answer
from agent_lab.evals.metrics import MetricDefinitionSet
from agent_lab.experiments.config import ResolvedExperiment
from agent_lab.experiments.tasks import Task
from agent_lab.tracing import events as ev
from agent_lab.tracing.events import TraceEvent

RESULT_SCHEMA_VERSION = "1.0.0"


class ToolCallRecord(BaseModel):
    """One substantive tool call, in emission order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int
    name: str
    arguments_json: str
    ok: bool
    error_kind: str | None


class ResultRow(BaseModel):
    """`SPEC.md` s13 (v2.2), plus explicit provenance for schema/version evolution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    execution_id: str
    experiment_id: str
    experiment_classification: str
    timestamp: str
    source_commit_sha: str | None = None
    source_tree_dirty: bool | None = None

    harness_version: str
    trace_schema_version: str
    result_schema_version: str = RESULT_SCHEMA_VERSION
    metric_definition_id: str
    metric_definition_fingerprint: str
    config_fingerprint: str
    task_set_fingerprint: str

    provider: str
    model: str
    model_parameters: str

    environment_id: str
    environment_version: str
    environment_fingerprint: str
    model_surface_fingerprint: str

    task_id: str
    task_set: str

    tool_space_id: str
    tool_count: int
    tool_names: tuple[str, ...]

    expected_tool: str
    expected_arguments: str

    tool_call_sequence: tuple[ToolCallRecord, ...]
    first_tool: str | None
    first_tool_arguments: str | None
    first_tool_correct: bool
    first_tool_arguments_correct: bool
    first_call_routing_correct: bool

    expected_tool_used: bool
    expected_tool_used_correctly: bool
    incorrect_tool_call_count: int
    unnecessary_tool_call_count: int
    tool_recovery_success: bool | None

    expected_answer: str
    actual_answer: str | None
    answer_strategy: str
    answer_detail: str
    task_success: bool

    stop_reason: str
    tool_call_count: int
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float | None

    repetition: int
    random_seed_if_applicable: int | None = None
    trace_path: str

    def metric_payload(self) -> dict[str, Any]:
        """The evaluated metrics, for the `EVALUATION_COMPLETED` trace event."""
        return {
            "first_tool": self.first_tool,
            "first_tool_arguments": self.first_tool_arguments,
            "first_tool_correct": self.first_tool_correct,
            "first_tool_arguments_correct": self.first_tool_arguments_correct,
            "first_call_routing_correct": self.first_call_routing_correct,
            "expected_tool_used": self.expected_tool_used,
            "expected_tool_used_correctly": self.expected_tool_used_correctly,
            "tool_recovery_success": self.tool_recovery_success,
            "incorrect_tool_call_count": self.incorrect_tool_call_count,
            "unnecessary_tool_call_count": self.unnecessary_tool_call_count,
            "tool_call_count": self.tool_call_count,
            "task_success": self.task_success,
            "answer_detail": self.answer_detail,
        }


class _Extracted(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    calls: tuple[ToolCallRecord, ...]
    final_text: str | None
    stop_reason: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float | None
    tool_names: tuple[str, ...]
    environment_id: str
    environment_version: str


def _extract(events: Sequence[TraceEvent]) -> _Extracted:
    """Reduce the ordered event stream to the facts metrics are computed from."""
    outcomes: dict[str, tuple[bool, str | None]] = {}
    for event in events:
        if event.event_type == ev.TOOL_CALL_EXECUTED:
            outcomes[str(event.payload["call_id"])] = (True, None)
        elif event.event_type == ev.TOOL_CALL_FAILED:
            outcomes[str(event.payload["call_id"])] = (False, str(event.payload["error_kind"]))

    calls: list[ToolCallRecord] = []
    for event in events:
        if event.event_type != ev.TOOL_CALL_REQUESTED:
            continue
        if not event.payload.get("attributable_to_model", False):
            # Harness-initiated retries are recorded but are not substantive model calls.
            continue
        call_id = str(event.payload["call_id"])
        ok, error_kind = outcomes.get(call_id, (False, "no_outcome_recorded"))
        calls.append(
            ToolCallRecord(
                sequence=event.sequence,
                name=str(event.payload["name"]),
                arguments_json=canonical_json(event.payload.get("arguments") or {}),
                ok=ok,
                error_kind=error_kind,
            )
        )

    final_text: str | None = None
    stop_reason = "unknown"
    latency_total = 0.0
    saw_latency = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_names: tuple[str, ...] = ()
    environment_id = ""
    environment_version = ""

    for event in events:
        if event.event_type == ev.RUN_COMPLETED:
            raw_text = event.payload.get("final_text")
            final_text = None if raw_text is None else str(raw_text)
            stop_reason = str(event.payload.get("stop_reason", "unknown"))
        elif event.event_type == ev.MODEL_RESPONSE:
            value = event.payload.get("latency_ms")
            if value is not None:
                latency_total += float(value)
                saw_latency = True
            raw_usage = event.payload.get("usage")
            if isinstance(raw_usage, dict):
                usage = cast(dict[str, Any], raw_usage)
                reported_input = usage.get("input_tokens")
                if reported_input is not None:
                    input_tokens = (input_tokens or 0) + int(reported_input)
                reported_output = usage.get("output_tokens")
                if reported_output is not None:
                    output_tokens = (output_tokens or 0) + int(reported_output)
        elif event.event_type == ev.ENVIRONMENT_CONNECTED:
            descriptor = cast(dict[str, Any], event.payload["descriptor"])
            declared_tools = cast(list[dict[str, Any]], descriptor["tools"])
            tool_names = tuple(sorted(str(tool["name"]) for tool in declared_tools))
            environment_id = str(descriptor["environment_id"])
            environment_version = str(descriptor["environment_version"])

    return _Extracted(
        calls=tuple(calls),
        final_text=final_text,
        stop_reason=stop_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_total if saw_latency else None,
        tool_names=tool_names,
        environment_id=environment_id,
        environment_version=environment_version,
    )


def derive_result(
    *,
    events: Sequence[TraceEvent],
    task: Task,
    resolved: ResolvedExperiment,
    metric_set: MetricDefinitionSet,
    trace_path: Path,
) -> ResultRow:
    """Compute a normalized row from trace events alone."""
    if not events:
        raise ValueError("cannot derive a result from an empty trace")
    head = events[0]
    started = next(e for e in events if e.event_type == ev.RUN_STARTED)
    extracted = _extract(events)

    expected_arguments = canonical_json(task.expected.arguments)

    def _is_expected(call: ToolCallRecord) -> bool:
        return call.name == task.expected.tool and call.arguments_json == expected_arguments

    first = extracted.calls[0] if extracted.calls else None
    first_tool_correct = first is not None and first.name == task.expected.tool
    first_arguments_correct = first is not None and first.arguments_json == expected_arguments
    primary = bool(first_tool_correct and first_arguments_correct)

    expected_used = any(call.name == task.expected.tool for call in extracted.calls)
    expected_used_correctly = any(_is_expected(call) for call in extracted.calls)

    first_correct_index = next(
        (index for index, call in enumerate(extracted.calls) if _is_expected(call)), None
    )
    unnecessary = (
        0 if first_correct_index is None else len(extracted.calls) - (first_correct_index + 1)
    )
    incorrect = sum(1 for call in extracted.calls if not _is_expected(call))

    success, detail = evaluate_answer(
        task.answer_strategy, extracted.final_text, task.expected.answer
    )

    return ResultRow(
        run_id=head.run_id,
        execution_id=head.execution_id,
        experiment_id=head.experiment_id,
        experiment_classification=resolved.config.classification,
        timestamp=head.timestamp,
        source_commit_sha=None,
        source_tree_dirty=None,
        harness_version=str(started.payload["harness_version"]),
        trace_schema_version=head.trace_schema_version,
        metric_definition_id=metric_set.id,
        metric_definition_fingerprint=metric_set.fingerprint(),
        config_fingerprint=str(started.payload["config_fingerprint"]),
        task_set_fingerprint=str(started.payload["task_set_fingerprint"]),
        provider=head.provider,
        model=head.model,
        model_parameters=canonical_json(resolved.config.model.parameters),
        environment_id=extracted.environment_id,
        environment_version=extracted.environment_version,
        environment_fingerprint=head.environment_fingerprint,
        model_surface_fingerprint=head.model_surface_fingerprint,
        task_id=task.id,
        task_set=resolved.task_set.id,
        tool_space_id=head.tool_space_id,
        tool_count=len(extracted.tool_names),
        tool_names=extracted.tool_names,
        expected_tool=task.expected.tool,
        expected_arguments=expected_arguments,
        tool_call_sequence=extracted.calls,
        first_tool=first.name if first else None,
        first_tool_arguments=first.arguments_json if first else None,
        first_tool_correct=bool(first_tool_correct),
        first_tool_arguments_correct=bool(first_arguments_correct),
        first_call_routing_correct=primary,
        expected_tool_used=expected_used,
        expected_tool_used_correctly=expected_used_correctly,
        incorrect_tool_call_count=incorrect,
        unnecessary_tool_call_count=unnecessary,
        # Null when no recovery was required (SPEC.md s14, v2.2).
        tool_recovery_success=None if primary else expected_used_correctly,
        expected_answer=canonical_json(task.expected.answer),
        actual_answer=extracted.final_text,
        answer_strategy=task.answer_strategy,
        answer_detail=detail,
        task_success=success,
        stop_reason=extracted.stop_reason,
        tool_call_count=len(extracted.calls),
        input_tokens=extracted.input_tokens,
        output_tokens=extracted.output_tokens,
        latency_ms=extracted.latency_ms,
        repetition=head.repetition,
        trace_path=str(trace_path),
    )
