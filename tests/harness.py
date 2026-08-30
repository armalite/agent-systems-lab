"""Shared helpers for harness tests: one real execution, reused across assertions."""

import asyncio
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from agent_lab.experiments.config import ResolvedExperiment, load_experiment
from agent_lab.experiments.result import ResultRow
from agent_lab.experiments.runner import ExecutionPaths, run_experiment
from agent_lab.tracing.events import TraceEvent

HARNESS_CHECK_CONFIG = Path("experiments/harness_check/experiment.yaml")

Execution = tuple[ExecutionPaths, tuple[ResultRow, ...]]


@lru_cache(maxsize=1)
def resolved_harness_check() -> ResolvedExperiment:
    return load_experiment(HARNESS_CHECK_CONFIG)


def execute(results_root: Path) -> Execution:
    """Run the harness-check experiment into a throwaway results root."""
    return asyncio.run(run_experiment(resolved_harness_check(), results_root=results_root))


def row_for(
    rows: tuple[ResultRow, ...], task_id: str, tool_space: str, repetition: int = 0
) -> ResultRow:
    for row in rows:
        if (
            row.task_id == task_id
            and row.tool_space_id == tool_space
            and row.repetition == repetition
        ):
            return row
    raise AssertionError(f"no row for {task_id} / {tool_space} / r{repetition}")


def canonical_trace(events: Sequence[TraceEvent]) -> list[dict[str, Any]]:
    return [event.canonical() for event in events]
