"""End-to-end harness behaviour: traces, derivation, determinism, and run identity.

These are the Milestone 2 acceptance properties. They run the real harness against the real MCP
environment with the deterministic scripted adapter - no external API is involved.
"""

import json
from pathlib import Path

import pytest

from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.result import derive_result
from agent_lab.experiments.runner import build_run_id
from agent_lab.tracing import events as ev
from agent_lab.tracing.recorder import read_trace
from tests.harness import Execution, canonical_trace, execute, resolved_harness_check

BASELINE = "customer_baseline_v1"
OVERLAP = "customer_overlap_v1"


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    root = tmp_path_factory.mktemp("results")
    return execute(root)


def test_every_cell_produces_a_row_and_a_trace(execution: Execution) -> None:
    paths, rows = execution
    resolved = resolved_harness_check()
    expected = (
        len(resolved.config.conditions)
        * len(resolved.selected_tasks())
        * resolved.config.repetitions
    )
    assert len(rows) == expected == 32
    assert len(list(paths.traces.glob("*.jsonl"))) == expected


def test_all_expected_artifacts_are_written(execution: Execution) -> None:
    paths, _ = execution
    assert paths.manifest.is_file()
    assert paths.resolved_config.is_file()
    assert paths.results.is_file()
    assert (paths.environments / f"{BASELINE}.json").is_file()
    assert (paths.environments / f"{OVERLAP}.json").is_file()


def test_manifest_records_provenance(execution: Execution) -> None:
    paths, rows = execution
    manifest = json.loads(paths.manifest.read_text())
    for key in (
        "execution_id",
        "harness_version",
        "trace_schema_version",
        "result_schema_version",
        "config_fingerprint",
        "task_set_fingerprint",
        "script_set_fingerprint",
        "metric_definition_id",
        "metric_definition_fingerprint",
        "lockfile_hash",
        "source_commit_sha",
        "source_tree_dirty",
    ):
        assert key in manifest, f"manifest missing {key}"
    assert manifest["run_count"] == len(rows)


def test_trace_sequence_is_monotonic_and_complete(execution: Execution) -> None:
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        events = read_trace(path)
        assert [e.sequence for e in events] == list(range(len(events)))
        types = [e.event_type for e in events]
        assert types[0] == ev.RUN_STARTED
        assert types[1] == ev.ENVIRONMENT_CONNECTED
        assert ev.RUN_COMPLETED in types
        assert types[-1] == ev.EVALUATION_COMPLETED


def test_every_tool_call_has_a_correlated_outcome(execution: Execution) -> None:
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        events = read_trace(path)
        requested = {e.payload["call_id"] for e in events if e.event_type == ev.TOOL_CALL_REQUESTED}
        resolved = {
            e.payload["call_id"]
            for e in events
            if e.event_type in (ev.TOOL_CALL_EXECUTED, ev.TOOL_CALL_FAILED)
        }
        assert requested == resolved, f"unmatched tool calls in {path.name}"


def test_layers_are_tagged_for_attribution(execution: Execution) -> None:
    paths, _ = execution
    seen: dict[str, set[str]] = {}
    for path in paths.traces.glob("*.jsonl"):
        for event in read_trace(path):
            seen.setdefault(event.event_type, set()).add(event.layer)
    assert seen[ev.MODEL_RESPONSE] == {"model"}
    assert seen[ev.TOOL_CALL_FAILED] == {"mcp"}
    assert seen[ev.TOOL_RESULT_RETURNED] == {"tool"}
    assert seen[ev.EVALUATION_COMPLETED] == {"evaluator"}


def test_results_are_reproducibly_derived_from_persisted_traces(execution: Execution) -> None:
    """The single most important harness test.

    Re-derive every row from the trace on disk and require equality with what was written. This
    is what makes "the raw trace is authoritative" a property rather than an intention.
    """
    paths, rows = execution
    resolved = resolved_harness_check()
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    for row in rows:
        events = read_trace(paths.root / row.trace_path)
        task = resolved.task_set.by_id(row.task_id)
        rederived = derive_result(
            events=events,
            task=task,
            resolved=resolved,
            metric_set=metric_set,
            trace_path=Path(row.trace_path),
        )
        assert rederived == row, f"re-derivation mismatch for {row.run_id}"


def test_derivation_ignores_the_evaluation_event(execution: Execution) -> None:
    """Re-derivation must not read back the evaluator's own conclusions."""
    paths, rows = execution
    resolved = resolved_harness_check()
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    row = rows[0]
    events = tuple(
        e
        for e in read_trace(paths.root / row.trace_path)
        if e.event_type != ev.EVALUATION_COMPLETED
    )
    rederived = derive_result(
        events=events,
        task=resolved.task_set.by_id(row.task_id),
        resolved=resolved,
        metric_set=metric_set,
        trace_path=Path(row.trace_path),
    )
    assert rederived == row


def test_repeated_executions_are_deterministic(tmp_path: Path) -> None:
    """Two physical executions differ only in volatile fields."""
    paths_a, rows_a = execute(tmp_path / "a")
    paths_b, rows_b = execute(tmp_path / "b")

    assert [r.run_id for r in rows_a] == [r.run_id for r in rows_b]
    volatile = {"execution_id", "timestamp", "latency_ms", "trace_path"}
    for a, b in zip(rows_a, rows_b, strict=True):
        assert a.model_dump(exclude=volatile) == b.model_dump(exclude=volatile)

    for trace_a in sorted(paths_a.traces.glob("*.jsonl")):
        trace_b = paths_b.traces / trace_a.name
        assert canonical_trace(read_trace(trace_a)) == canonical_trace(read_trace(trace_b))


def test_logical_run_id_is_stable_and_execution_id_is_not(tmp_path: Path) -> None:
    """Stable logical identity, non-overwriting physical identity (`SPEC.md` s12)."""
    paths_a, rows_a = execute(tmp_path / "a")
    paths_b, rows_b = execute(tmp_path / "b")
    assert {r.run_id for r in rows_a} == {r.run_id for r in rows_b}
    assert rows_a[0].execution_id != rows_b[0].execution_id
    assert paths_a.root != paths_b.root
    assert paths_a.root.exists() and paths_b.root.exists()


def test_run_id_format() -> None:
    assert build_run_id("exp", "space", "task", 2) == "exp/space/task/r2"


def test_reruns_into_the_same_root_never_overwrite(tmp_path: Path) -> None:
    """Even two executions starting in the same second must both keep their evidence."""
    root = tmp_path / "shared"
    paths_a, rows_a = execute(root)
    paths_b, rows_b = execute(root)
    assert paths_a.root != paths_b.root
    assert paths_a.results.is_file() and paths_b.results.is_file()
    assert len(list(paths_a.traces.glob("*.jsonl"))) == len(rows_a)
    assert len(list(paths_b.traces.glob("*.jsonl"))) == len(rows_b)
    assert {r.run_id for r in rows_a} == {r.run_id for r in rows_b}


def test_execution_id_appends_a_counter_on_collision(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from agent_lab.experiments.runner import build_execution_id

    moment = datetime(2026, 8, 30, 12, 0, 0, tzinfo=UTC)
    root = tmp_path / "exp"
    root.mkdir()
    first = build_execution_id(moment, root)
    (root / first).mkdir()
    second = build_execution_id(moment, root)
    assert first == "20260830T120000Z"
    assert second == "20260830T120000Z-2"
