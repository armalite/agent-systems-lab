# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
#
# pyarrow ships no type information, so iterating RESULT_SCHEMA's fields is Unknown to a
# strict checker. Scoped to the modules that touch pyarrow, as in storage/parquet.py.
"""Phase 0 analysis: unit of generalization, clustering, strata separation, validity gating.

Uses synthetic result rows so the analysis is testable without any execution or provider call.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from agent_lab.analysis.phase0 import (
    BOOTSTRAP_SEED,
    DIRECT,
    NON_TARGET,
    PRACTICAL_EFFECT_THRESHOLD,
    OperationallyIncompleteError,
    analyse,
    assert_operationally_complete,
    bootstrap_ci,
    compare_tasks,
    summarize_stratum,
)
from agent_lab.storage.parquet import RESULT_SCHEMA, write_results

BASELINE = "customer_baseline_v1"
OVERLAP = "customer_overlap_v1"


def _row(task_id: str, condition: str, rep: int, correct: bool, **over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {field.name: None for field in RESULT_SCHEMA}
    row.update(
        task_id=task_id,
        tool_space_id=condition,
        repetition=rep,
        first_call_routing_correct=correct,
        provider_error_kind=None,
    )
    row.update(over)
    return row


def _cell(task_id: str, condition: str, n_correct: int, reps: int = 5) -> list[dict[str, Any]]:
    return [_row(task_id, condition, i, i < n_correct) for i in range(reps)]


# ------------------------------------------------------------------ aggregation


def test_task_is_the_unit_and_repetitions_are_replicates() -> None:
    """5 correct of 5 -> 1.0; 3 of 5 -> 0.6. Runs never become task observations."""
    rows = _cell("t1", BASELINE, 5) + _cell("t1", OVERLAP, 3)
    for r in rows:
        r["exposure"] = DIRECT
    (comparison,) = compare_tasks(rows, BASELINE, OVERLAP)
    assert comparison.baseline_rate == 1.0
    assert comparison.overlap_rate == 0.6
    assert comparison.difference == pytest.approx(-0.4)
    assert comparison.baseline_runs == comparison.overlap_runs == 5


def test_mean_paired_difference_is_over_tasks_not_runs() -> None:
    rows: list[dict[str, Any]] = []
    # one task fully regresses, three unchanged -> mean difference = -0.25, not -1/20
    for i, (b, o) in enumerate([(5, 0), (5, 5), (5, 5), (5, 5)]):
        rows += _cell(f"t{i}", BASELINE, b) + _cell(f"t{i}", OVERLAP, o)
    for r in rows:
        r["exposure"] = DIRECT
    summary = summarize_stratum(compare_tasks(rows, BASELINE, OVERLAP), DIRECT)
    assert summary.mean_difference == pytest.approx(-0.25)
    assert len(summary.tasks) == 4


def test_descriptive_counts() -> None:
    rows: list[dict[str, Any]] = []
    for i, (b, o) in enumerate([(5, 2), (5, 5), (3, 5)]):
        rows += _cell(f"t{i}", BASELINE, b) + _cell(f"t{i}", OVERLAP, o)
    for r in rows:
        r["exposure"] = DIRECT
    summary = summarize_stratum(compare_tasks(rows, BASELINE, OVERLAP), DIRECT)
    assert (summary.regressed, summary.unchanged, summary.improved) == (1, 1, 1)


def test_missing_pair_member_is_an_error() -> None:
    rows = _cell("t1", BASELINE, 5)
    for r in rows:
        r["exposure"] = DIRECT
    with pytest.raises(ValueError, match="pairing is broken"):
        compare_tasks(rows, BASELINE, OVERLAP)


# ------------------------------------------------------------------ strata


def test_strata_are_never_pooled() -> None:
    rows: list[dict[str, Any]] = []
    for i in range(3):  # direct: big regression
        rows += _cell(f"d{i}", BASELINE, 5) + _cell(f"d{i}", OVERLAP, 0)
    for i in range(3):  # non-target: unchanged
        rows += _cell(f"n{i}", BASELINE, 5) + _cell(f"n{i}", OVERLAP, 5)
    for r in rows:
        r["exposure"] = DIRECT if r["task_id"].startswith("d") else NON_TARGET
    comparisons = compare_tasks(rows, BASELINE, OVERLAP)
    direct = summarize_stratum(comparisons, DIRECT)
    non_target = summarize_stratum(comparisons, NON_TARGET)
    assert direct.mean_difference == pytest.approx(-1.0)
    assert non_target.mean_difference == pytest.approx(0.0)
    # Pooling would have diluted the headline to -0.5; it must not.
    assert len(direct.tasks) == 3
    assert all(t.exposure == DIRECT for t in direct.tasks)


# ------------------------------------------------------------------ bootstrap


def test_bootstrap_is_deterministic_under_the_fixed_seed() -> None:
    """Reproducible, and immune to global RNG state - it must use its own seeded generator."""
    import random as _random

    diffs = [-0.2, 0.0, -0.6, 0.2, 0.0, -0.4, 0.0, -0.2]
    assert bootstrap_ci(diffs) == bootstrap_ci(diffs)

    _random.seed(1)
    first = bootstrap_ci(diffs)
    _random.seed(999_999)
    assert bootstrap_ci(diffs) == first


def test_bootstrap_resamples_tasks_not_runs() -> None:
    """Zero variance across tasks must give a zero-width interval, whatever the run count."""
    low, high = bootstrap_ci([-0.4] * 12)
    assert low == pytest.approx(-0.4)
    assert high == pytest.approx(-0.4)


def test_bootstrap_interval_brackets_the_mean() -> None:
    diffs = [-1.0, -0.8, -0.2, 0.0, 0.0, 0.2, -0.4, -0.6, 0.0, -0.2]
    low, high = bootstrap_ci(diffs)
    mean = sum(diffs) / len(diffs)
    assert low <= mean <= high


def test_practical_threshold_is_the_approved_value() -> None:
    assert PRACTICAL_EFFECT_THRESHOLD == 0.10


# ------------------------------------------------------------------ operational validity


def test_operationally_incomplete_execution_is_refused() -> None:
    rows = _cell("t1", BASELINE, 5) + _cell("t1", OVERLAP, 5)
    rows[3]["provider_error_kind"] = "rate_limit"
    with pytest.raises(OperationallyIncompleteError, match="invalidates the whole execution"):
        assert_operationally_complete(rows)


def test_failed_rows_are_never_silently_dropped() -> None:
    rows = _cell("t1", BASELINE, 5) + _cell("t1", OVERLAP, 5)
    rows[0]["provider_error_kind"] = "api_status_error"
    with pytest.raises(OperationallyIncompleteError) as info:
        assert_operationally_complete(rows)
    assert "never silently dropped" in str(info.value)


def test_complete_execution_passes_the_gate() -> None:
    assert_operationally_complete(_cell("t1", BASELINE, 5) + _cell("t1", OVERLAP, 5))


# ------------------------------------------------------------------ end to end


def _write_execution(root: Path, *, failed: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    for i in range(4):
        rows += _cell(f"d{i}", BASELINE, 5) + _cell(f"d{i}", OVERLAP, 3)
        tasks.append({"id": f"d{i}", "metadata": {"exposure": DIRECT}})
    for i in range(2):
        rows += _cell(f"n{i}", BASELINE, 5) + _cell(f"n{i}", OVERLAP, 5)
        tasks.append({"id": f"n{i}", "metadata": {"exposure": NON_TARGET}})
    if failed:
        rows[0]["provider_error_kind"] = "rate_limit"
    for row in rows:
        # `_row` seeds every schema field with None, so these list columns must be assigned
        # outright - setdefault would leave the None in place.
        row["tool_names"] = ()
        row["tool_call_sequence"] = ()
        row["provider_request_ids"] = ()
    from agent_lab.experiments.result import ResultRow

    typed = [ResultRow.model_construct(**row) for row in rows]
    write_results(root / "results.parquet", typed)
    (root / "resolved_config.json").write_text(
        json.dumps({"config": {"conditions": [BASELINE, OVERLAP]}, "task_set": {"tasks": tasks}})
    )
    return root


def test_analyse_produces_the_pre_registered_report(tmp_path: Path) -> None:
    report = analyse(_write_execution(tmp_path / "exec"))
    assert report["unit_of_generalization"] == "task"
    assert report["bootstrap"]["cluster"] == "task"
    assert report["bootstrap"]["resamples"] == 10_000
    assert report["bootstrap"]["seed"] == BOOTSTRAP_SEED
    head = report["headline_direct_exposure"]
    assert head["n_tasks"] == 4
    assert head["mean_paired_difference"] == pytest.approx(-0.4)
    assert report["non_target_spillover"]["n_tasks"] == 2
    assert report["non_target_spillover"]["mean_paired_difference"] == pytest.approx(0.0)


def test_analyse_refuses_an_operationally_incomplete_execution(tmp_path: Path) -> None:
    with pytest.raises(OperationallyIncompleteError):
        analyse(_write_execution(tmp_path / "bad", failed=True))


def test_chart_renders_offline(tmp_path: Path) -> None:
    from agent_lab.analysis.phase0 import render_chart

    root = _write_execution(tmp_path / "exec")
    report_rows = analyse(root)
    assert report_rows["headline_direct_exposure"]["n_tasks"] == 4
    rows = [
        _row(f"d{i}", c, r, True) for i in range(2) for c in (BASELINE, OVERLAP) for r in range(2)
    ]
    for row in rows:
        row["exposure"] = DIRECT
    summary = summarize_stratum(compare_tasks(rows, BASELINE, OVERLAP), DIRECT)
    out = render_chart([summary], tmp_path / "chart.png")
    assert out.is_file() and out.stat().st_size > 0
