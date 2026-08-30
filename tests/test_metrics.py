"""Metric semantics, asserted scenario by scenario against a real execution.

Each harness-check task exercises one behaviour class. The expected values below are the
metric definitions restated independently, so a change to the implementation that alters
semantics fails here rather than silently reinterpreting results.
"""

import pytest

from agent_lab.evals.metrics import METRIC_DEFINITION_SETS, PHASE0_SINGLE_TOOL_V1
from agent_lab.experiments.result import ResultRow
from tests.harness import execute, row_for

BASELINE = "customer_baseline_v1"
OVERLAP = "customer_overlap_v1"


@pytest.fixture(scope="module")
def rows(tmp_path_factory: pytest.TempPathFactory) -> tuple[ResultRow, ...]:
    return execute(tmp_path_factory.mktemp("metrics"))[1]


# task, condition, primary, first_tool_correct, first_args_correct, used, used_ok,
# recovery, incorrect, unnecessary, calls, success
CASES = [
    ("hc_001_correct_first_call", OVERLAP, True, True, True, True, True, None, 0, 0, 1, True),
    (
        "hc_002_wrong_tool_then_recover",
        OVERLAP,
        False,
        False,
        True,
        True,
        True,
        True,
        1,
        0,
        2,
        True,
    ),
    (
        "hc_002_wrong_tool_then_recover",
        BASELINE,
        False,
        False,
        True,
        True,
        True,
        True,
        1,
        0,
        2,
        True,
    ),
    (
        "hc_003_bad_arguments_then_recover",
        OVERLAP,
        False,
        True,
        False,
        True,
        True,
        True,
        1,
        0,
        2,
        True,
    ),
    (
        "hc_004_wrong_tool_no_recovery",
        OVERLAP,
        False,
        False,
        False,
        False,
        False,
        False,
        1,
        0,
        1,
        False,
    ),
    (
        "hc_005_unknown_tool_then_recover",
        OVERLAP,
        False,
        False,
        True,
        True,
        True,
        True,
        1,
        0,
        2,
        True,
    ),
    ("hc_006_unnecessary_extra_call", OVERLAP, True, True, True, True, True, None, 0, 1, 2, True),
    ("hc_007_no_tool_call", OVERLAP, False, False, False, False, False, False, 0, 0, 0, False),
    ("hc_008_failure_no_answer", OVERLAP, True, True, True, True, True, None, 0, 0, 1, False),
]


@pytest.mark.parametrize(
    (
        "task_id",
        "condition",
        "primary",
        "ftc",
        "fac",
        "used",
        "used_ok",
        "recovery",
        "incorrect",
        "unnecessary",
        "calls",
        "success",
    ),
    CASES,
    ids=[f"{case[0]}::{case[1].split('_')[1]}" for case in CASES],
)
def test_metric_outcomes(
    rows: tuple[ResultRow, ...],
    task_id: str,
    condition: str,
    primary: bool,
    ftc: bool,
    fac: bool,
    used: bool,
    used_ok: bool,
    recovery: bool | None,
    incorrect: int,
    unnecessary: int,
    calls: int,
    success: bool,
) -> None:
    row = row_for(rows, task_id, condition)
    assert row.first_call_routing_correct is primary
    assert row.first_tool_correct is ftc
    assert row.first_tool_arguments_correct is fac
    assert row.expected_tool_used is used
    assert row.expected_tool_used_correctly is used_ok
    assert row.tool_recovery_success is recovery
    assert row.incorrect_tool_call_count == incorrect
    assert row.unnecessary_tool_call_count == unnecessary
    assert row.tool_call_count == calls
    assert row.task_success is success


def test_recovery_is_null_exactly_when_no_recovery_was_required(
    rows: tuple[ResultRow, ...],
) -> None:
    """`SPEC.md` s14 (v2.2): null means not-applicable, not failure."""
    for row in rows:
        if row.first_call_routing_correct:
            assert row.tool_recovery_success is None
        else:
            assert row.tool_recovery_success is not None


def test_task_success_is_independent_of_tool_use(rows: tuple[ResultRow, ...]) -> None:
    """Routing and answer correctness must be separately measurable (`SPEC.md` s9.3)."""
    failed_routing_but_answered = [
        r for r in rows if not r.first_call_routing_correct and r.task_success
    ]
    correct_routing_but_wrong_answer = [
        r for r in rows if r.first_call_routing_correct and not r.task_success
    ]
    assert failed_routing_but_answered, "expected at least one recovery case"
    assert correct_routing_but_wrong_answer, "expected at least one correct-route/no-answer case"


def test_unknown_tool_is_recorded_as_a_substantive_call(rows: tuple[ResultRow, ...]) -> None:
    """A hallucinated tool name is a routing failure, not an invisible event (`SPEC.md` s12)."""
    row = row_for(rows, "hc_005_unknown_tool_then_recover", OVERLAP)
    first = row.tool_call_sequence[0]
    assert first.name == "fetch_employee_record"
    assert first.ok is False
    assert first.error_kind == "unknown_tool"
    assert row.tool_call_count == 2


def test_same_script_different_surface_changes_the_trace(rows: tuple[ResultRow, ...]) -> None:
    """Identical model behaviour meeting a different capability surface must be visible."""
    baseline = row_for(rows, "hc_002_wrong_tool_then_recover", BASELINE)
    overlap = row_for(rows, "hc_002_wrong_tool_then_recover", OVERLAP)
    assert baseline.tool_call_sequence[0].error_kind == "unknown_tool"
    assert overlap.tool_call_sequence[0].error_kind is None
    assert baseline.first_call_routing_correct == overlap.first_call_routing_correct


def test_stop_reasons_are_recorded(rows: tuple[ResultRow, ...]) -> None:
    assert row_for(rows, "hc_001_correct_first_call", OVERLAP).stop_reason == "answered"
    assert row_for(rows, "hc_008_failure_no_answer", OVERLAP).stop_reason == "no_answer"


def test_metric_definition_provenance_is_recorded(rows: tuple[ResultRow, ...]) -> None:
    metric_set = METRIC_DEFINITION_SETS[PHASE0_SINGLE_TOOL_V1]
    for row in rows:
        assert row.metric_definition_id == PHASE0_SINGLE_TOOL_V1
        assert row.metric_definition_fingerprint == metric_set.fingerprint()


def test_metric_fingerprint_changes_when_semantics_change() -> None:
    """Editing a definition in place must be detectable, not silent."""
    original = METRIC_DEFINITION_SETS[PHASE0_SINGLE_TOOL_V1]
    tweaked = original.model_copy(update={"specification": original.specification + "\n# changed"})
    assert tweaked.fingerprint() != original.fingerprint()


def test_token_usage_is_null_not_zero(rows: tuple[ResultRow, ...]) -> None:
    """The fake adapter reports no usage; recording 0 would fabricate a measurement."""
    for row in rows:
        assert row.input_tokens is None
        assert row.output_tokens is None
