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
from agent_lab.models.provider import PAID_PROVIDERS
from agent_lab.synthetic.toolspaces import TOOL_SPACES

Classification = Literal["harness_check", "calibration", "characterisation", "frontier"]


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AdapterSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["scripted", "anthropic"]
    """`scripted` is deterministic and free. `anthropic` can incur cost and is refused unless
    the operator passes --allow-paid for that invocation."""

    script_set: str | None = None

    def model_post_init(self, _context: Any) -> None:
        if self.kind == "scripted" and not self.script_set:
            raise ValueError("the scripted adapter requires a script_set")
        if self.kind != "scripted" and self.script_set:
            raise ValueError(f"adapter kind {self.kind!r} does not take a script_set")


class Controls(BaseModel):
    """Everything held constant across conditions. A declared change here invalidates
    comparison with earlier results (`SPEC.md` s16)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system_instructions: str
    max_steps: int = Field(ge=1)
    retries: int = Field(default=0, ge=0)
    randomize_tool_order: bool = False


class CostControls(BaseModel):
    """Hard ceiling on provider requests, enforced at call time (`SPEC.md` s19)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_provider_requests: int = Field(ge=1)


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
    cost_controls: CostControls | None = None

    @property
    def can_incur_cost(self) -> bool:
        return self.model.provider in PAID_PROVIDERS

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
        if self.model.provider in PAID_PROVIDERS:
            if self.cost_controls is None:
                raise ValueError(
                    f"experiment {self.id}: provider {self.model.provider!r} can incur cost and "
                    "requires a cost_controls.max_provider_requests ceiling"
                )
            if "temperature" in self.model.parameters:
                raise ValueError(
                    f"experiment {self.id}: temperature is unsupported on current Claude models "
                    "and is rejected by the API; declare thinking/effort controls instead "
                    "(SPEC.md s18, v2.3)"
                )
            if "max_tokens" not in self.model.parameters:
                raise ValueError(
                    f"experiment {self.id}: model.parameters.max_tokens must be declared "
                    "explicitly rather than inherited from a provider default"
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
    task_fp = task_set.fingerprint()
    if config.adapter.script_set:
        script_fp = load_script_set(directory / config.adapter.script_set).fingerprint()
    else:
        script_fp = fingerprint(None)
    return ResolvedExperiment(
        config=config,
        task_set=task_set,
        directory=directory,
        config_fingerprint=config.fingerprint(task_fp, script_fp),
        task_set_fingerprint=task_fp,
        script_set_fingerprint=script_fp,
    )
