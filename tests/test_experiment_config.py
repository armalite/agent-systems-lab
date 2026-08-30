"""Configuration, task, and script-set validation."""

from pathlib import Path

import pytest
import yaml

from agent_lab.experiments.config import ExperimentConfig, load_experiment
from agent_lab.experiments.tasks import Task, TaskSet, load_task_set
from agent_lab.models.fake import ScriptSet, load_script_set

CONFIG = Path("experiments/harness_check/experiment.yaml")


def _raw() -> dict[str, object]:
    return yaml.safe_load(CONFIG.read_text())


def test_harness_check_config_resolves() -> None:
    resolved = load_experiment(CONFIG)
    assert resolved.config.id == "harness_check_001"
    assert resolved.config.classification == "harness_check"


def test_harness_check_is_not_labelled_calibration() -> None:
    """Phase 0 calibration is Milestone 4 and requires pre-registration first."""
    assert load_experiment(CONFIG).config.classification != "calibration"


def test_unknown_condition_is_rejected() -> None:
    raw = _raw()
    raw["conditions"] = ["customer_baseline_v1", "does_not_exist_v1"]
    with pytest.raises(ValueError, match="unknown tool-space"):
        ExperimentConfig.model_validate(raw)


def test_unknown_metric_set_is_rejected() -> None:
    raw = _raw()
    raw["metric_definition_set"] = "made_up_v9"
    with pytest.raises(ValueError, match="unknown metric definition set"):
        ExperimentConfig.model_validate(raw)


def test_duplicate_conditions_are_rejected() -> None:
    raw = _raw()
    raw["conditions"] = ["customer_baseline_v1", "customer_baseline_v1"]
    with pytest.raises(ValueError, match="duplicate conditions"):
        ExperimentConfig.model_validate(raw)


def test_unknown_config_keys_are_rejected() -> None:
    """Silent ignoring would let an uncontrolled variable hide in the config."""
    raw = _raw()
    raw["temperature"] = 0.7
    with pytest.raises(ValueError):
        ExperimentConfig.model_validate(raw)


def test_only_the_scripted_adapter_is_accepted() -> None:
    raw = _raw()
    raw["adapter"] = {"kind": "anthropic", "script_set": "scripts.yaml"}
    with pytest.raises(ValueError):
        ExperimentConfig.model_validate(raw)


def test_task_set_loads_with_declared_answer_strategies() -> None:
    task_set = load_task_set(Path("experiments/harness_check/tasks.yaml"))
    assert len(task_set.tasks) == 8
    assert {task.answer_strategy for task in task_set.tasks} == {
        "contains_facts",
        "exact_match",
        "typed_scalar",
    }


def test_unknown_answer_strategy_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown answer strategy"):
        Task.model_validate(
            {
                "id": "t",
                "prompt": "p",
                "expected": {"tool": "get_customer", "arguments": {}, "answer": {"value": "x"}},
                "answer_strategy": "vibes",
            }
        )


def test_duplicate_task_ids_are_rejected() -> None:
    task = {
        "id": "dup",
        "prompt": "p",
        "expected": {"tool": "get_customer", "arguments": {}, "answer": {"value": "x"}},
        "answer_strategy": "exact_match",
    }
    with pytest.raises(ValueError, match="duplicate task ids"):
        TaskSet.model_validate({"id": "s", "version": "1", "tasks": [task, task]})


def test_fingerprints_are_content_sensitive() -> None:
    task_set = load_task_set(Path("experiments/harness_check/tasks.yaml"))
    changed = task_set.model_copy(
        update={
            "tasks": (
                task_set.tasks[0].model_copy(update={"prompt": "different"}),
                *task_set.tasks[1:],
            )
        }
    )
    assert changed.fingerprint() != task_set.fingerprint()


def test_task_set_fingerprint_is_order_insensitive() -> None:
    task_set = load_task_set(Path("experiments/harness_check/tasks.yaml"))
    reordered = task_set.model_copy(update={"tasks": tuple(reversed(task_set.tasks))})
    assert reordered.fingerprint() == task_set.fingerprint()


def test_config_fingerprint_covers_referenced_content() -> None:
    """Changing a task must change the config fingerprint even though the YAML is untouched."""
    resolved = load_experiment(CONFIG)
    other = resolved.config.fingerprint("different-task-fp", resolved.script_set_fingerprint)
    assert other != resolved.config_fingerprint


def test_script_set_resolution_prefers_exact_condition_match() -> None:
    scripts = load_script_set(Path("experiments/harness_check/scripts.yaml"))
    baseline = scripts.resolve("hc_002_wrong_tool_then_recover", "customer_baseline_v1")
    overlap = scripts.resolve("hc_002_wrong_tool_then_recover", "customer_overlap_v1")
    assert baseline.scenario == "wrong_tool_then_recover_unknown"
    assert overlap.scenario == "wrong_tool_then_recover"


def test_wildcard_script_applies_to_every_condition() -> None:
    scripts = load_script_set(Path("experiments/harness_check/scripts.yaml"))
    for condition in ("customer_baseline_v1", "customer_overlap_v1"):
        assert (
            scripts.resolve("hc_001_correct_first_call", condition).scenario == "correct_first_call"
        )


def test_missing_script_raises_rather_than_inferring_behaviour() -> None:
    """The fake adapter must never fall back to ground truth."""
    scripts = ScriptSet(id="s", version="1", scripts=())
    with pytest.raises(KeyError, match="never infers behaviour"):
        scripts.resolve("unscripted_task", "customer_baseline_v1")
