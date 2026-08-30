"""Declarative experiment configuration.

The resolved config must capture every variable needed to reproduce or compare a run
(`SPEC.md` s18). Anything not represented here cannot honestly be claimed as controlled, so the
model forbids unknown keys rather than silently ignoring them.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from agent_lab.environments.surface import fingerprint
from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.tasks import TaskSet, load_task_set
from agent_lab.synthetic.toolspaces import TOOL_SPACES

Classification = Literal["harness_check", "calibration", "characterisation", "frontier"]


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AdapterSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["scripted"]
    """Only the deterministic scripted adapter exists. Real providers arrive in Milestone 3,
    and adding one here must be a deliberate, reviewable change."""

    script_set: str


class Controls(BaseModel):
    """Everything held constant across conditions. A declared change here invalidates
    comparison with earlier results (`SPEC.md` s16)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system_instructions: str
    max_steps: int = Field(ge=1)
    retries: int = Field(default=0, ge=0)
    randomize_tool_order: bool = False


class Limits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_tasks: int | None = Field(default=None, ge=1)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    classification: Classification
    research_question: str
    model: ModelSpec
    adapter: AdapterSpec
    task_set: str
    conditions: tuple[str, ...]
    repetitions: int = Field(ge=1)
    controls: Controls
    metric_definition_set: str
    limits: Limits = Field(default_factory=Limits)

    def model_post_init(self, _context: Any) -> None:
        if not self.conditions:
            raise ValueError(f"experiment {self.id}: at least one condition is required")
        if len(set(self.conditions)) != len(self.conditions):
            raise ValueError(f"experiment {self.id}: duplicate conditions")
        for condition in self.conditions:
            if condition not in TOOL_SPACES:
                raise ValueError(
                    f"experiment {self.id}: unknown tool-space {condition!r}; "
                    f"known: {tuple(sorted(TOOL_SPACES))}"
                )
        if self.metric_definition_set not in METRIC_DEFINITION_SETS:
            raise ValueError(
                f"experiment {self.id}: unknown metric definition set "
                f"{self.metric_definition_set!r}; known: {sorted(METRIC_DEFINITION_SETS)}"
            )

    def fingerprint(self, task_set_fingerprint: str, script_set_fingerprint: str) -> str:
        """Hash of the fully resolved configuration, including referenced content."""
        return fingerprint(
            {
                "config": self.model_dump(mode="json"),
                "task_set_fingerprint": task_set_fingerprint,
                "script_set_fingerprint": script_set_fingerprint,
            }
        )


class ResolvedExperiment(BaseModel):
    """A config plus every artifact it references, loaded and fingerprinted."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    config: ExperimentConfig
    task_set: TaskSet
    directory: Path
    config_fingerprint: str
    task_set_fingerprint: str
    script_set_fingerprint: str

    def selected_tasks(self) -> tuple[Any, ...]:
        """Apply the cost-control task cap deterministically, in declared order."""
        tasks = self.task_set.tasks
        if self.config.limits.max_tasks is not None:
            return tasks[: self.config.limits.max_tasks]
        return tasks


def load_experiment(path: Path) -> ResolvedExperiment:
    """Load and fully resolve an experiment definition from its directory."""
    from agent_lab.models.fake import load_script_set

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: experiment config must be a YAML mapping")
    config = ExperimentConfig.model_validate(raw)
    directory = path.parent
    task_set = load_task_set(directory / config.task_set)
    script_set = load_script_set(directory / config.adapter.script_set)
    task_fp = task_set.fingerprint()
    script_fp = script_set.fingerprint()
    return ResolvedExperiment(
        config=config,
        task_set=task_set,
        directory=directory,
        config_fingerprint=config.fingerprint(task_fp, script_fp),
        task_set_fingerprint=task_fp,
        script_set_fingerprint=script_fp,
    )
