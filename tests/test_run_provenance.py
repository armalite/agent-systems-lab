# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
#
# pyarrow ships no type information, so iterating RESULT_SCHEMA's fields is Unknown to a
# strict checker. Scoped to the modules that touch pyarrow, as in storage/parquet.py.
"""Source provenance and schedule index enter the raw trace, then are derived into the row.

`SPEC.md` s18 evidence hierarchy: the trace is authoritative and the normalized row is derived
from it. Git provenance is never injected into Parquet independently of the raw evidence.
"""

import json
from pathlib import Path

import pytest

from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, derive_result
from agent_lab.storage.parquet import RESULT_SCHEMA, read_results
from agent_lab.tracing import events as ev
from agent_lab.tracing.events import TRACE_SCHEMA_VERSION
from agent_lab.tracing.recorder import read_trace
from tests.harness import Execution, execute, resolved_harness_check


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    return execute(tmp_path_factory.mktemp("provenance"))


def test_schema_versions_were_bumped() -> None:
    assert TRACE_SCHEMA_VERSION == "1.3.0"
    assert RESULT_SCHEMA_VERSION == "1.3.0"


def test_provenance_enters_the_raw_trace_first(execution: Execution) -> None:
    paths, _ = execution
    for path in paths.traces.glob("*.jsonl"):
        started = next(e for e in read_trace(path) if e.event_type == ev.RUN_STARTED)
        assert "source_commit_sha" in started.payload
        assert "source_tree_dirty" in started.payload
        assert "schedule_index" in started.payload
        assert "task_index" in started.payload


def test_rows_derive_provenance_from_that_trace(execution: Execution) -> None:
    paths, rows = execution
    for row in rows:
        started = next(
            e for e in read_trace(paths.root / row.trace_path) if e.event_type == ev.RUN_STARTED
        )
        assert row.source_commit_sha == started.payload["source_commit_sha"]
        assert row.source_tree_dirty == started.payload["source_tree_dirty"]
        assert row.workspace_commit_sha == started.payload["workspace_commit_sha"]
        assert row.workspace_tree_dirty == started.payload["workspace_tree_dirty"]
        assert row.schedule_index == started.payload["schedule_index"]


def test_schedule_index_is_always_populated(execution: Execution) -> None:
    _, rows = execution
    assert all(row.schedule_index is not None for row in rows)


def test_git_provenance_is_populated_inside_a_repository(execution: Execution) -> None:
    """The M3 gap: the columns existed but every row was null.

    Outside a git working tree `source_commit_sha` is legitimately None - the runner degrades
    gracefully rather than inventing provenance - so this asserts the populated case only where
    it is meaningful. Derivation-from-trace is asserted unconditionally elsewhere. The real
    Phase 0 run additionally requires a clean committed tree.
    """
    paths, rows = execution
    manifest = json.loads(paths.manifest.read_text())
    if manifest["source_commit_sha"] is None:
        pytest.skip("not executing inside a git working tree")
    assert all(row.source_commit_sha for row in rows)
    assert all(row.source_tree_dirty is not None for row in rows)


def test_provenance_matches_the_manifest(execution: Execution) -> None:
    paths, rows = execution
    manifest = json.loads(paths.manifest.read_text())
    assert {row.source_commit_sha for row in rows} == {manifest["source_commit_sha"]}
    assert {row.source_tree_dirty for row in rows} == {manifest["source_tree_dirty"]}


def test_provenance_survives_to_parquet(execution: Execution) -> None:
    paths, _ = execution
    assert "schedule_index" in {field.name for field in RESULT_SCHEMA}
    records = read_results(paths.results)
    assert all(r["schedule_index"] is not None for r in records)
    manifest = json.loads(paths.manifest.read_text())
    expected = manifest["source_commit_sha"]
    assert all(r["source_commit_sha"] == expected for r in records)


def test_re_derivation_equality_still_holds(execution: Execution) -> None:
    """The M2 guarantee must survive the schema bump."""
    paths, rows = execution
    resolved = resolved_harness_check()
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    for row in rows:
        rederived = derive_result(
            events=read_trace(paths.root / row.trace_path),
            task=resolved.task_set.by_id(row.task_id),
            resolved=resolved,
            metric_set=metric_set,
            trace_path=Path(row.trace_path),
        )
        assert rederived == row


def test_derivation_reads_only_the_trace(execution: Execution) -> None:
    """Stripping provenance from the trace must strip it from the derived row - proving the row
    is not populated from an independent source."""
    paths, rows = execution
    resolved = resolved_harness_check()
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    row = rows[0]
    events = list(read_trace(paths.root / row.trace_path))
    started = events[0]
    stripped = started.model_copy(
        update={
            "payload": {
                k: v
                for k, v in started.payload.items()
                if k
                not in {
                    "source_commit_sha",
                    "source_tree_dirty",
                    "workspace_commit_sha",
                    "workspace_tree_dirty",
                    "schedule_index",
                }
            }
        }
    )
    rederived = derive_result(
        events=[stripped, *events[1:]],
        task=resolved.task_set.by_id(row.task_id),
        resolved=resolved,
        metric_set=metric_set,
        trace_path=Path(row.trace_path),
    )
    assert rederived.source_commit_sha is None
    assert rederived.source_tree_dirty is None
    assert rederived.workspace_commit_sha is None
    assert rederived.workspace_tree_dirty is None
    assert rederived.schedule_index is None
