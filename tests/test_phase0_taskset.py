"""The frozen Phase 0 task set and experiment configuration.

Everything here is checked offline against the fixtures: no model, no provider, no cost.
"""

from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest

from agent_lab.evals.answers import evaluate_answer
from agent_lab.evals.metrics import PHASE0_SINGLE_TOOL_V1
from agent_lab.experiments.config import load_experiment
from agent_lab.experiments.tasks import TaskSet, load_task_set
from agent_lab.synthetic.toolspaces import TOOL_DEFINITIONS, TOOL_SPACES

CONFIG = Path("experiments/phase0_calibration/experiment.yaml")
TASKS = Path("experiments/phase0_calibration/tasks.yaml")
BASELINE = "customer_baseline_v1"
OVERLAP = "customer_overlap_v1"


@pytest.fixture(scope="module")
def task_set() -> TaskSet:
    return load_task_set(TASKS)


# ------------------------------------------------------------------ composition


def test_exactly_28_tasks(task_set: TaskSet) -> None:
    assert len(task_set.tasks) == 28


def test_strata_are_20_direct_and_8_non_target(task_set: TaskSet) -> None:
    counts = Counter(t.metadata["exposure"] for t in task_set.tasks)
    assert counts == {"direct": 20, "non_target": 8}


def test_direct_stratum_is_entirely_customer_id_lookups(task_set: TaskSet) -> None:
    """A task keyed on name or email would make an overlap-only tool correct and be
    unanswerable in baseline, breaking the pairing."""
    for task in task_set.tasks:
        if task.metadata["exposure"] != "direct":
            continue
        assert task.expected.tool == "get_customer"
        assert set(task.expected.arguments) == {"customer_id"}


def test_direct_stratum_balances_fields_and_registers(task_set: TaskSet) -> None:
    direct = [t for t in task_set.tasks if t.metadata["exposure"] == "direct"]
    assert Counter(t.metadata["field"] for t in direct) == {
        "email": 5,
        "city": 5,
        "status": 5,
        "name": 5,
    }
    assert Counter(t.metadata["register"] for t in direct) == {
        "direct": 5,
        "imperative": 5,
        "stated_need": 5,
        "trailing_id": 5,
    }


def test_non_target_stratum_spans_four_entities(task_set: TaskSet) -> None:
    non_target = [t for t in task_set.tasks if t.metadata["exposure"] == "non_target"]
    assert Counter(t.metadata["entity"] for t in non_target) == {
        "order": 2,
        "invoice": 2,
        "product": 2,
        "employee": 2,
    }


def test_every_task_uses_a_distinct_fixture_record(task_set: TaskSet) -> None:
    """Reusing a record would be pseudo-replication: the same routing decision twice."""
    records = [next(iter(t.expected.arguments.values())) for t in task_set.tasks]
    assert len(set(records)) == len(records) == 28


def test_all_twenty_customer_records_are_used_once(task_set: TaskSet) -> None:
    ids = sorted(
        str(t.expected.arguments["customer_id"])
        for t in task_set.tasks
        if t.metadata["exposure"] == "direct"
    )
    assert ids == [f"C{100 + i}" for i in range(1, 21)]


def test_prompts_are_unique_and_not_paraphrase_duplicates(task_set: TaskSet) -> None:
    prompts = [t.prompt for t in task_set.tasks]
    assert len(set(prompts)) == 28
    # No two tasks share both field and register within a stratum.
    keys = [
        (t.metadata["exposure"], t.metadata["field"], t.metadata["register"])
        for t in task_set.tasks
    ]
    assert len(set(keys)) >= 20


def test_exact_match_is_never_used(task_set: TaskSet) -> None:
    """M3 evidence: a conversational model answers in prose, so exact_match would fail on
    correct answers and inject matcher artifacts into task_success."""
    assert all(t.answer_strategy != "exact_match" for t in task_set.tasks)
    assert set(t.answer_strategy for t in task_set.tasks) <= {"contains_facts", "typed_scalar"}


# ------------------------------------------------------------------ answerability


def test_every_expected_tool_exists_in_both_conditions(task_set: TaskSet) -> None:
    for task in task_set.tasks:
        assert task.expected.tool in TOOL_SPACES[BASELINE]
        assert task.expected.tool in TOOL_SPACES[OVERLAP]


def test_every_task_is_answerable_from_the_frozen_fixtures(task_set: TaskSet) -> None:
    for task in task_set.tasks:
        outcome = cast(
            dict[str, Any],
            TOOL_DEFINITIONS[task.expected.tool].fn(**task.expected.arguments).model_dump(),
        )
        assert outcome["found"] is True, f"{task.id}: {outcome.get('message')}"
        # Cast inside the generator: narrowing by isinstance still yields dict[Unknown, Unknown].
        record = next(
            cast(dict[str, Any], value) for value in outcome.values() if isinstance(value, dict)
        )
        field = task.metadata["field"]
        expected_value = (
            task.expected.answer["value"]
            if "value" in task.expected.answer
            else task.expected.answer[field]
        )
        assert str(record[field]).casefold() == str(expected_value).casefold(), task.id


def test_declared_strategy_accepts_a_faithful_answer(task_set: TaskSet) -> None:
    for task in task_set.tasks:
        values = " and ".join(str(v) for k, v in task.expected.answer.items() if k != "type")
        ok, detail = evaluate_answer(
            task.answer_strategy, f"The answer is {values}.", task.expected.answer
        )
        assert ok, f"{task.id}: {detail}"


# ------------------------------------------------------------------ configuration


def test_experiment_is_frozen_as_approved() -> None:
    resolved = load_experiment(CONFIG)
    config = resolved.config
    assert config.classification == "calibration"
    assert config.conditions == (BASELINE, OVERLAP)
    assert config.repetitions == 5
    assert len(resolved.selected_tasks()) == 28
    assert config.metric_definition_set == PHASE0_SINGLE_TOOL_V1
    assert config.model.name == "claude-opus-5"
    assert config.model.parameters["thinking"] == {"type": "adaptive"}
    assert config.model.parameters["output_config"] == {"effort": "high"}
    assert config.model.parameters["max_tokens"] == 4096
    assert "temperature" not in config.model.parameters
    assert config.controls.max_steps == 4
    assert config.controls.retries == 0


def test_request_ceiling_cannot_truncate_a_valid_trajectory() -> None:
    """`SPEC.md` s14.1 (v2.5): the ceiling must permit every path valid under max_steps."""
    resolved = load_experiment(CONFIG)
    config = resolved.config
    worst_case = (
        len(resolved.selected_tasks())
        * len(config.conditions)
        * config.repetitions
        * config.controls.max_steps
    )
    assert worst_case == 1120
    assert config.cost_controls is not None
    assert config.cost_controls.max_provider_requests >= worst_case


def test_planned_run_count_is_280() -> None:
    resolved = load_experiment(CONFIG)
    runs = (
        len(resolved.selected_tasks())
        * len(resolved.config.conditions)
        * resolved.config.repetitions
    )
    assert runs == 280


def test_phase0_still_requires_explicit_paid_authorization() -> None:
    from typer.testing import CliRunner

    from agent_lab.cli import app

    result = CliRunner().invoke(app, ["run", str(CONFIG)])
    assert result.exit_code == 2
    assert "--allow-paid" in result.stdout
