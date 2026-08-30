"""Task and task-set loading.

Tasks are declarative YAML. A task set carries an id, a version, and a content hash, so a
result row can name exactly which frozen dataset produced it.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from agent_lab.environments.surface import fingerprint
from agent_lab.evals.answers import ANSWER_STRATEGIES


class ExpectedOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    answer: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """One deterministic task with an independently measurable tool and answer expectation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    prompt: str
    expected: ExpectedOutcome
    answer_strategy: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, _context: Any) -> None:
        if self.answer_strategy not in ANSWER_STRATEGIES:
            raise ValueError(
                f"task {self.id}: unknown answer strategy {self.answer_strategy!r}; "
                f"known: {sorted(ANSWER_STRATEGIES)}"
            )


class TaskSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    tasks: tuple[Task, ...]

    def model_post_init(self, _context: Any) -> None:
        ids = [task.id for task in self.tasks]
        if len(set(ids)) != len(ids):
            raise ValueError(f"task set {self.id} contains duplicate task ids")
        if not self.tasks:
            raise ValueError(f"task set {self.id} is empty")

    def fingerprint(self) -> str:
        """Content hash over the frozen task definitions, ordered by task id."""
        return fingerprint(
            {
                "id": self.id,
                "version": self.version,
                "tasks": [
                    task.model_dump(mode="json") for task in sorted(self.tasks, key=lambda t: t.id)
                ],
            }
        )

    def by_id(self, task_id: str) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"no task {task_id!r} in task set {self.id}")


def load_task_set(path: Path) -> TaskSet:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: task set must be a YAML mapping")
    return TaskSet.model_validate(raw)
