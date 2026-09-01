"""Deterministic counterbalanced execution order (`SPEC.md` s14.1, s16, v2.5).

Execution order is experimental design: running every baseline observation before every overlap
observation would confound condition with time, provider state, and a mutable model alias.
"""

import json
from itertools import pairwise
from pathlib import Path

import pytest

from agent_lab.experiments.runner import ScheduleEntry, build_schedule
from tests.harness import Execution, execute

CONDITIONS = ("customer_baseline_v1", "customer_overlap_v1")
TASKS = [f"t{i:02d}" for i in range(6)]


def _schedule(reps: int = 4) -> tuple[ScheduleEntry, ...]:
    return build_schedule(CONDITIONS, TASKS, reps)


def test_schedule_covers_every_cell_exactly_once() -> None:
    schedule = _schedule()
    cells = {(e.task_id, e.tool_space_id, e.repetition) for e in schedule}
    assert len(schedule) == len(cells) == len(TASKS) * len(CONDITIONS) * 4


def test_schedule_index_is_dense_and_ordered() -> None:
    schedule = _schedule()
    assert [e.schedule_index for e in schedule] == list(range(len(schedule)))


def test_schedule_is_deterministic() -> None:
    """A pure function of frozen task order and repetition count - no RNG, so no seed."""
    assert _schedule() == _schedule()


def test_conditions_of_a_task_repetition_run_adjacently() -> None:
    """Pair adjacency is what protects the paired analysis from drift between its members."""
    schedule = _schedule()
    for first, second in zip(schedule[::2], schedule[1::2], strict=True):
        assert first.task_id == second.task_id
        assert first.repetition == second.repetition
        assert {first.tool_space_id, second.tool_space_id} == set(CONDITIONS)
        assert second.schedule_index == first.schedule_index + 1


def test_within_pair_order_alternates_and_balances() -> None:
    """Neither condition may be systematically first."""
    schedule = _schedule()
    firsts = [schedule[i].tool_space_id for i in range(0, len(schedule), 2)]
    counts = {c: firsts.count(c) for c in CONDITIONS}
    assert counts[CONDITIONS[0]] == counts[CONDITIONS[1]]

    for entry in schedule[::2]:
        forward = (entry.task_index + entry.repetition) % 2 == 0
        assert entry.tool_space_id == (CONDITIONS[0] if forward else CONDITIONS[1])


def test_a_task_leads_with_each_condition_across_repetitions() -> None:
    schedule = _schedule()
    leads = [e.tool_space_id for e in schedule[::2] if e.task_id == "t00"]
    assert set(leads) == set(CONDITIONS)


def test_conditions_interleave_rather_than_block() -> None:
    """The failure mode this replaces: all baseline runs, then all overlap runs."""
    order = [e.tool_space_id for e in _schedule()]
    switches = sum(1 for a, b in pairwise(order) if a != b)
    assert switches > len(order) // 2


def test_single_condition_experiments_keep_declared_order() -> None:
    schedule = build_schedule(("only_v1",), TASKS, 2)
    assert {e.tool_space_id for e in schedule} == {"only_v1"}
    assert len(schedule) == len(TASKS) * 2


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    return execute(tmp_path_factory.mktemp("schedule"))


def test_realized_schedule_is_persisted_in_the_manifest(execution: Execution) -> None:
    paths, rows = execution
    manifest = json.loads(paths.manifest.read_text())
    assert "schedule_rule" in manifest
    schedule = manifest["schedule"]
    assert len(schedule) == len(rows)
    assert [s["schedule_index"] for s in schedule] == list(range(len(rows)))


def test_runs_execute_in_schedule_order(execution: Execution) -> None:
    paths, rows = execution
    manifest = json.loads(paths.manifest.read_text())
    by_index = {s["schedule_index"]: s for s in manifest["schedule"]}
    for row in rows:
        assert row.schedule_index is not None
        entry = by_index[row.schedule_index]
        assert entry["task_id"] == row.task_id
        assert entry["tool_space_id"] == row.tool_space_id
        assert entry["repetition"] == row.repetition
    # rows are appended in execution order
    assert [r.schedule_index for r in rows] == sorted(r.schedule_index or 0 for r in rows)


def test_harness_check_execution_is_actually_interleaved(execution: Execution) -> None:
    _, rows = execution
    order = [r.tool_space_id for r in rows]
    switches = sum(1 for a, b in pairwise(order) if a != b)
    assert switches > len(order) // 2, "conditions must not execute in blocks"


def test_both_environments_are_described_in_one_execution(execution: Execution) -> None:
    paths, _ = execution
    assert len(list(paths.environments.glob("*.json"))) == 2
    for path in paths.environments.glob("*.json"):
        data = json.loads(Path(path).read_text())
        assert data["environment_fingerprint"].startswith("fp1:sha256:")
