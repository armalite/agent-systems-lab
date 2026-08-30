"""Trace event model and JSONL round-tripping."""

from pathlib import Path
from typing import Any

from agent_lab.tracing.events import TRACE_SCHEMA_VERSION, TraceEvent
from agent_lab.tracing.recorder import TraceRecorder, read_trace

CONTEXT: dict[str, Any] = {
    "run_id": "exp/space/task/r0",
    "execution_id": "20260830T000000Z",
    "experiment_id": "exp",
    "task_id": "task",
    "repetition": 0,
    "tool_space_id": "space",
    "environment_fingerprint": "fp1:sha256:env",
    "model_surface_fingerprint": "fp1:sha256:surface",
    "provider": "fake",
    "model": "scripted-v1",
}


def test_recorder_writes_ordered_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    with TraceRecorder(path, dict(CONTEXT)) as recorder:
        recorder.emit("A", "harness", {"i": 0})
        recorder.emit("B", "model", {"i": 1})
        recorder.emit("C", "evaluator", {"i": 2})

    events = read_trace(path)
    assert [e.event_type for e in events] == ["A", "B", "C"]
    assert [e.sequence for e in events] == [0, 1, 2]
    assert all(e.trace_schema_version == TRACE_SCHEMA_VERSION for e in events)


def test_trace_survives_a_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    with TraceRecorder(path, dict(CONTEXT)) as recorder:
        written = recorder.emit("A", "model", {"nested": {"b": [1, 2, 3]}})
    assert read_trace(path)[0] == written


def test_read_trace_orders_by_sequence_not_file_order(tmp_path: Path) -> None:
    """Ordering must survive tooling that does not preserve line order."""
    path = tmp_path / "run.jsonl"
    with TraceRecorder(path, dict(CONTEXT)) as recorder:
        recorder.emit("A", "harness")
        recorder.emit("B", "harness")
    lines = path.read_text().splitlines()
    path.write_text("\n".join(reversed(lines)) + "\n")
    assert [e.event_type for e in read_trace(path)] == ["A", "B"]


def test_canonical_view_strips_only_volatile_fields() -> None:
    event = TraceEvent(
        sequence=0,
        timestamp="2026-08-30T00:00:00+00:00",
        layer="model",
        event_type="MODEL_RESPONSE",
        payload={"latency_ms": 12.5, "text": "hello"},
        **CONTEXT,
    )
    canonical = event.canonical()
    assert "timestamp" not in canonical
    assert "execution_id" not in canonical
    assert "latency_ms" not in canonical["payload"]
    assert canonical["payload"]["text"] == "hello"
    assert canonical["run_id"] == CONTEXT["run_id"]


def test_unknown_event_fields_are_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        TraceEvent(
            sequence=0,
            timestamp="t",
            layer="model",
            event_type="X",
            unexpected="nope",  # type: ignore[call-arg]
            **CONTEXT,
        )
