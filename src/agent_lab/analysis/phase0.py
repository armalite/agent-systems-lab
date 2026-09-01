"""Phase 0 calibration analysis.

One script for one frozen experiment, not a statistics framework. It reads only persisted
evidence and computes exactly what `research/preregistration/PHASE0.md` declares in advance.

Three rules are enforced here rather than left to discipline:

1. **The task is the unit of generalization.** Repetitions are within-task replicates; they are
   never counted as independent task observations, and the bootstrap resamples *tasks*, keeping
   each task's repetitions clustered.
2. **Strata are never pooled.** The headline is the 20 direct-exposure tasks. The 8 non-target
   tasks are reported separately as a coarse spillover indicator.
3. **An operationally incomplete execution yields no headline.** If any run failed for a
   provider reason, the analysis refuses rather than silently dropping rows.
"""

import json
import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agent_lab.storage.parquet import read_results

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260901
"""Fixed so the interval is reproducible. The value carries no inferential meaning."""

PRACTICAL_EFFECT_THRESHOLD = 0.10
"""Smallest mean paired routing difference considered practically meaningful for this
calibration. Not an MDE, not a power estimate, not a significance threshold, and not a
requirement for Phase 0 to succeed (`SPEC.md` s16)."""

DIRECT = "direct"
NON_TARGET = "non_target"


class OperationallyIncompleteError(RuntimeError):
    """Raised when an execution contains a provider failure.

    The pre-registered rule invalidates the whole physical execution rather than dropping cells,
    so the headline must not be computed from it (`SPEC.md` s14.1, v2.5).
    """


@dataclass(frozen=True)
class TaskComparison:
    task_id: str
    exposure: str
    baseline_rate: float
    overlap_rate: float
    baseline_runs: int
    overlap_runs: int

    @property
    def difference(self) -> float:
        return self.overlap_rate - self.baseline_rate


@dataclass(frozen=True)
class StratumSummary:
    exposure: str
    tasks: tuple[TaskComparison, ...]
    mean_difference: float
    ci_low: float
    ci_high: float
    regressed: int
    unchanged: int
    improved: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "exposure": self.exposure,
            "n_tasks": len(self.tasks),
            "mean_paired_difference": self.mean_difference,
            "bootstrap_ci_95": [self.ci_low, self.ci_high],
            "regressed": self.regressed,
            "unchanged": self.unchanged,
            "improved": self.improved,
            "per_task": [
                {
                    "task_id": t.task_id,
                    "baseline_rate": t.baseline_rate,
                    "overlap_rate": t.overlap_rate,
                    "difference": t.difference,
                    "baseline_runs": t.baseline_runs,
                    "overlap_runs": t.overlap_runs,
                }
                for t in self.tasks
            ],
        }


def assert_operationally_complete(rows: Sequence[dict[str, Any]]) -> None:
    """Refuse to analyse an execution containing any provider failure."""
    failed = [r for r in rows if r.get("provider_error_kind") is not None]
    if failed:
        kinds = sorted({str(r["provider_error_kind"]) for r in failed})
        raise OperationallyIncompleteError(
            f"{len(failed)} of {len(rows)} runs failed for provider reasons {kinds}. Under the "
            "pre-registered rule this invalidates the whole execution: retain it as apparatus "
            "evidence, resolve the operational cause, and rerun the frozen experiment under a "
            "new execution_id with fresh authorization. Runs are never silently dropped."
        )


def compare_tasks(
    rows: Sequence[dict[str, Any]], baseline: str, overlap: str
) -> tuple[TaskComparison, ...]:
    """Run rows -> per-task, per-condition routing rate -> paired difference."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    exposure: dict[str, str] = {}
    for row in rows:
        task_id = str(row["task_id"])
        grouped.setdefault((task_id, str(row["tool_space_id"])), []).append(row)
        exposure.setdefault(task_id, str(row.get("exposure") or ""))

    comparisons: list[TaskComparison] = []
    for task_id in sorted({str(row["task_id"]) for row in rows}):
        base_runs = grouped.get((task_id, baseline), [])
        over_runs = grouped.get((task_id, overlap), [])
        if not base_runs or not over_runs:
            raise ValueError(f"task {task_id} is not present in both conditions; pairing is broken")
        comparisons.append(
            TaskComparison(
                task_id=task_id,
                exposure=exposure[task_id],
                baseline_rate=_rate(base_runs),
                overlap_rate=_rate(over_runs),
                baseline_runs=len(base_runs),
                overlap_runs=len(over_runs),
            )
        )
    return tuple(comparisons)


def _rate(runs: Sequence[dict[str, Any]]) -> float:
    correct = sum(1 for r in runs if bool(r["first_call_routing_correct"]))
    return correct / len(runs)


def bootstrap_ci(
    differences: Sequence[float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Percentile CI for the mean paired difference, resampling **tasks**.

    Tasks are the resampling unit, so every repetition belonging to a task moves together - a
    task's rate is already its cluster summary. Resampling runs instead would treat within-task
    replicates as independent observations, which the pre-registration forbids.
    """
    if not differences:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(differences)
    means: list[float] = []
    for _ in range(resamples):
        sample = [differences[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    return (means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1])


def summarize_stratum(comparisons: Sequence[TaskComparison], exposure: str) -> StratumSummary:
    selected = tuple(c for c in comparisons if c.exposure == exposure)
    diffs = [c.difference for c in selected]
    low, high = bootstrap_ci(diffs)
    return StratumSummary(
        exposure=exposure,
        tasks=selected,
        mean_difference=statistics.fmean(diffs) if diffs else float("nan"),
        ci_low=low,
        ci_high=high,
        regressed=sum(1 for d in diffs if d < 0),
        unchanged=sum(1 for d in diffs if d == 0),
        improved=sum(1 for d in diffs if d > 0),
    )


def _attach_exposure(rows: list[dict[str, Any]], task_set: dict[str, Any]) -> None:
    """Stratum labels come from the frozen task set, not from the result rows."""
    declared = cast(list[dict[str, Any]], task_set["tasks"])
    exposure = {
        str(task["id"]): str(cast(dict[str, Any], task.get("metadata") or {}).get("exposure", ""))
        for task in declared
    }
    for row in rows:
        row["exposure"] = exposure.get(str(row["task_id"]), "")


def render_chart(summaries: Sequence[StratumSummary], path: Path) -> Path:
    """The one comparison chart required by `SPEC.md` s16."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(summaries), figsize=(6 * len(summaries), 4.5), squeeze=False)
    for ax, summary in zip(axes[0], summaries, strict=True):
        diffs = [t.difference for t in summary.tasks]
        labels = [t.task_id for t in summary.tasks]
        ax.barh(range(len(diffs)), diffs, color=["#c0392b" if d < 0 else "#7f8c8d" for d in diffs])
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=7)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.axvline(
            summary.mean_difference,
            color="#2980b9",
            linestyle="--",
            linewidth=1.2,
            label=f"mean {summary.mean_difference:+.3f}",
        )
        ax.set_xlabel("overlap - baseline first-call routing rate")
        ax.set_title(f"{summary.exposure} (n={len(summary.tasks)})")
        ax.set_xlim(-1.05, 1.05)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)  # pyright: ignore[reportUnknownMemberType]  # partial stubs
    plt.close(fig)
    return path


def analyse(execution_dir: Path) -> dict[str, Any]:
    """Compute the pre-registered Phase 0 analysis from one persisted execution."""
    rows = read_results(execution_dir / "results.parquet")
    assert_operationally_complete(rows)

    resolved = json.loads((execution_dir / "resolved_config.json").read_text(encoding="utf-8"))
    _attach_exposure(rows, resolved["task_set"])
    baseline, overlap = resolved["config"]["conditions"]

    comparisons = compare_tasks(rows, baseline, overlap)
    direct = summarize_stratum(comparisons, DIRECT)
    non_target = summarize_stratum(comparisons, NON_TARGET)

    return {
        "execution": execution_dir.name,
        "baseline_condition": baseline,
        "overlap_condition": overlap,
        "unit_of_generalization": "task",
        "repetitions_are": "within-task replicates",
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "cluster": "task"},
        "practical_effect_threshold": PRACTICAL_EFFECT_THRESHOLD,
        "headline_direct_exposure": direct.as_dict(),
        "non_target_spillover": non_target.as_dict(),
        "notes": [
            "Headline is the direct-exposure stratum only; strata are never pooled.",
            "The non-target stratum (n=8) is a coarse spillover indicator, not a negative control.",
            "The practical-effect threshold is not an MDE, power estimate, or success requirement.",
        ],
    }


def main(execution_dir: Path) -> None:
    report = analyse(execution_dir)
    (execution_dir / "phase0_analysis.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    rows = read_results(execution_dir / "results.parquet")
    resolved = json.loads((execution_dir / "resolved_config.json").read_text(encoding="utf-8"))
    _attach_exposure(rows, resolved["task_set"])
    baseline, overlap = resolved["config"]["conditions"]
    comparisons = compare_tasks(rows, baseline, overlap)
    render_chart(
        [summarize_stratum(comparisons, DIRECT), summarize_stratum(comparisons, NON_TARGET)],
        execution_dir / "phase0_comparison.png",
    )
    head = report["headline_direct_exposure"]
    print(f"execution                {report['execution']}")
    print(
        f"headline (direct, n={head['n_tasks']})  mean paired difference "
        f"{head['mean_paired_difference']:+.4f}"
    )
    print(
        f"  95% task-cluster CI    [{head['bootstrap_ci_95'][0]:+.4f}, "
        f"{head['bootstrap_ci_95'][1]:+.4f}]"
    )
    print(
        f"  regressed/unchanged/improved  {head['regressed']}/{head['unchanged']}"
        f"/{head['improved']}"
    )
    spill = report["non_target_spillover"]
    print(
        f"non-target (n={spill['n_tasks']}, descriptive)  mean "
        f"{spill['mean_paired_difference']:+.4f}"
    )
    print(f"wrote {execution_dir / 'phase0_analysis.json'}")
    print(f"wrote {execution_dir / 'phase0_comparison.png'}")


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]))
