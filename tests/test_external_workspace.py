# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
#
# pyarrow ships no type information, so iterating RESULT_SCHEMA's fields is Unknown to a
# strict checker. Scoped as in storage/parquet.py.
"""External research workspaces: two provenance domains, never conflated by CWD.

`SPEC.md` s12.1 and s18.1 (v2.6/v2.7): the reusable apparatus and the repository holding a study's
definition are distinct provenance domains. Apparatus provenance is resolved from the installed
`agent_lab` package; workspace provenance from the worktree containing the experiment definition.
Neither is ever inferred from the process working directory.

Temporary Git repositories stand in for a real research workspace, so these tests are hermetic
and never touch a researcher's actual private repo.
"""

import asyncio
import json
import os
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest

from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.config import load_experiment
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, ResultRow, derive_result
from agent_lab.experiments.runner import (
    ExecutionPaths,
    apparatus_lockfile_hash,
    apparatus_provenance,
    apparatus_root,
    run_experiment,
    workspace_provenance,
)
from agent_lab.storage.parquet import RESULT_SCHEMA, read_results
from agent_lab.tracing import events as ev
from agent_lab.tracing.events import TRACE_SCHEMA_VERSION
from agent_lab.tracing.recorder import read_trace

HARNESS_CHECK = Path("experiments/harness_check").resolve()
APPARATUS = Path(__file__).resolve().parent.parent


@contextmanager
def working_directory(path: Path) -> Generator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def make_workspace(root: Path, *, study: str = "study-a", commit: bool = True) -> Path:
    """A throwaway research workspace: a Git repo holding a copy of an experiment definition."""
    experiment_dir = root / "experiments" / study
    experiment_dir.mkdir(parents=True)
    for name in ("experiment.yaml", "tasks.yaml", "scripts.yaml"):
        shutil.copy(HARNESS_CHECK / name, experiment_dir / name)
    (root / "results").mkdir(exist_ok=True)
    if commit:
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "test@example.test")
        _git(root, "config", "user.name", "Test")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "workspace")
    return experiment_dir


def workspace_head(root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


# ------------------------------------------------------------------ apparatus domain


def test_apparatus_root_is_the_agent_systems_lab_repository() -> None:
    assert apparatus_root() == APPARATUS
    assert (APPARATUS / "src" / "agent_lab").is_dir()


def test_apparatus_provenance_is_independent_of_cwd(tmp_path: Path) -> None:
    """The v2.6 defect: provenance used to follow whichever directory the caller stood in."""
    baseline = apparatus_provenance()
    seen = [baseline]
    for target in (tmp_path, Path("/tmp"), Path.home()):
        with working_directory(target):
            seen.append(apparatus_provenance())
    assert all(entry == baseline for entry in seen)
    assert baseline["source_commit_sha"]


def test_an_unrelated_cwd_git_repo_cannot_replace_apparatus_provenance(tmp_path: Path) -> None:
    other = tmp_path / "unrelated"
    other.mkdir()
    (other / "file.txt").write_text("x")
    _git(other, "init", "-q")
    _git(other, "config", "user.email", "t@example.test")
    _git(other, "config", "user.name", "T")
    _git(other, "add", "-A")
    _git(other, "commit", "-qm", "unrelated")

    with working_directory(other):
        captured = apparatus_provenance()
    assert captured["source_commit_sha"] != workspace_head(other)
    assert captured["source_commit_sha"] == apparatus_provenance()["source_commit_sha"]


def test_apparatus_lockfile_hash_is_cwd_independent(tmp_path: Path) -> None:
    baseline = apparatus_lockfile_hash()
    assert baseline is not None and baseline.startswith("sha256:")
    with working_directory(tmp_path):
        assert apparatus_lockfile_hash() == baseline


# ------------------------------------------------------------------ workspace domain


def test_workspace_provenance_resolves_from_a_nested_experiment_directory(tmp_path: Path) -> None:
    """An experiment sits several directories deep; the Git top-level must still be found."""
    workspace = tmp_path / "research"
    workspace.mkdir()
    experiment_dir = make_workspace(workspace)
    captured = workspace_provenance(experiment_dir)
    assert captured["workspace_commit_sha"] == workspace_head(workspace)
    assert captured["workspace_tree_dirty"] is False


def test_workspace_dirty_state_is_captured(tmp_path: Path) -> None:
    workspace = tmp_path / "research"
    workspace.mkdir()
    experiment_dir = make_workspace(workspace)
    assert workspace_provenance(experiment_dir)["workspace_tree_dirty"] is False
    (workspace / "notes.md").write_text("uncommitted")
    assert workspace_provenance(experiment_dir)["workspace_tree_dirty"] is True


def test_non_git_experiment_directory_yields_null_workspace_provenance(tmp_path: Path) -> None:
    """Explicitly unavailable - never a CWD fallback (`SPEC.md` s12.1)."""
    plain = tmp_path / "plain"
    experiment_dir = make_workspace(plain, commit=False)
    with working_directory(APPARATUS):
        captured = workspace_provenance(experiment_dir)
    assert captured == {"workspace_commit_sha": None, "workspace_tree_dirty": None}


def test_the_two_domains_are_independent(tmp_path: Path) -> None:
    workspace = tmp_path / "research"
    workspace.mkdir()
    experiment_dir = make_workspace(workspace)
    apparatus = apparatus_provenance()
    ws = workspace_provenance(experiment_dir)
    assert apparatus["source_commit_sha"] != ws["workspace_commit_sha"]
    # The apparatus tree's dirty state must not be taken from the workspace's, or vice versa.
    (workspace / "dirty.md").write_text("x")
    assert workspace_provenance(experiment_dir)["workspace_tree_dirty"] is True
    assert apparatus_provenance() == apparatus


# ------------------------------------------------------------------ end to end


class ExternalRun(NamedTuple):
    """One execution driven from a throwaway research workspace."""

    paths: ExecutionPaths
    rows: tuple[ResultRow, ...]
    workspace: Path
    experiment_dir: Path


@pytest.fixture(scope="module")
def external_run(tmp_path_factory: pytest.TempPathFactory) -> ExternalRun:
    """The supported workflow: external experiment definition, external results root."""
    workspace = tmp_path_factory.mktemp("research")
    experiment_dir = make_workspace(workspace)
    resolved = load_experiment(experiment_dir / "experiment.yaml")
    paths, rows = asyncio.run(run_experiment(resolved, results_root=workspace / "results"))
    return ExternalRun(paths, rows, workspace, experiment_dir)


def test_external_experiment_runs_and_writes_into_the_workspace(external_run: ExternalRun) -> None:
    paths, rows, workspace, _ = external_run
    assert len(rows) == 32
    assert paths.root.is_relative_to(workspace)
    assert len(list(paths.traces.glob("*.jsonl"))) == 32


def test_both_domains_enter_run_started(external_run: ExternalRun) -> None:
    paths, _, workspace, _ = external_run
    for path in list(paths.traces.glob("*.jsonl"))[:3]:
        started = next(e for e in read_trace(path) if e.event_type == ev.RUN_STARTED)
        assert started.payload["source_commit_sha"] == apparatus_provenance()["source_commit_sha"]
        assert started.payload["workspace_commit_sha"] == workspace_head(workspace)


def test_rows_record_apparatus_and_workspace_separately(external_run: ExternalRun) -> None:
    _, rows, workspace, _ = external_run
    apparatus_sha = apparatus_provenance()["source_commit_sha"]
    for row in rows:
        assert row.source_commit_sha == apparatus_sha
        assert row.workspace_commit_sha == workspace_head(workspace)
        assert row.source_commit_sha != row.workspace_commit_sha


def test_manifest_persists_both_domains(external_run: ExternalRun) -> None:
    paths, _, workspace, _ = external_run
    manifest = json.loads(paths.manifest.read_text())
    assert manifest["source_commit_sha"] == apparatus_provenance()["source_commit_sha"]
    assert manifest["workspace_commit_sha"] == workspace_head(workspace)
    assert manifest["workspace_tree_dirty"] is not None
    assert manifest["lockfile_hash"] is not None, "apparatus lockfile must survive an external run"


def test_trace_path_is_execution_root_relative_and_has_no_absolute_path(
    external_run: ExternalRun,
) -> None:
    """`SPEC.md` s13 (v2.7): an external results root must not leak a developer-machine path."""
    paths, rows, _, _ = external_run
    for row in rows:
        assert not Path(row.trace_path).is_absolute()
        assert row.trace_path.startswith("traces/")
        assert "/home/" not in row.trace_path
        assert str(paths.root) not in row.trace_path
        assert (paths.root / row.trace_path).is_file()


def test_no_absolute_paths_leak_into_normalized_evidence(external_run: ExternalRun) -> None:
    paths, _, workspace, _ = external_run
    blob = json.dumps(read_results(paths.results), default=str)
    assert str(workspace) not in blob
    assert str(Path.home()) not in blob


def test_schema_versions_are_1_3_0(external_run: ExternalRun) -> None:
    _, rows, _, _ = external_run
    assert TRACE_SCHEMA_VERSION == RESULT_SCHEMA_VERSION == "1.3.0"
    assert all(r.trace_schema_version == "1.3.0" for r in rows)
    assert all(r.result_schema_version == "1.3.0" for r in rows)


def test_parquet_round_trips_workspace_fields(external_run: ExternalRun) -> None:
    paths, _, workspace, _ = external_run
    names = {field.name for field in RESULT_SCHEMA}
    assert {"workspace_commit_sha", "workspace_tree_dirty"} <= names
    records = read_results(paths.results)
    assert all(r["workspace_commit_sha"] == workspace_head(workspace) for r in records)
    assert all(r["workspace_tree_dirty"] is False for r in records)


def test_re_derivation_equality_holds_for_an_external_run(external_run: ExternalRun) -> None:
    paths, rows, _, experiment_dir = external_run
    resolved = load_experiment(experiment_dir / "experiment.yaml")
    metric_set = METRIC_DEFINITION_SETS[resolved.config.metric_definition_set]
    for row in rows:
        rederived = derive_result(
            events=read_trace(paths.root / row.trace_path),
            task=resolved.task_set.by_id(row.task_id),
            resolved=resolved,
            metric_set=metric_set,
            trace_path=Path(row.trace_path),
        )
        assert rederived == row


def test_external_fingerprints_match_the_in_repo_definition(external_run: ExternalRun) -> None:
    """Copying an experiment into a workspace must not change what binds it."""
    _, _, _, experiment_dir = external_run
    external = load_experiment(experiment_dir / "experiment.yaml")
    in_repo = load_experiment(HARNESS_CHECK / "experiment.yaml")
    assert external.config_fingerprint == in_repo.config_fingerprint
    assert external.task_set_fingerprint == in_repo.task_set_fingerprint
    assert external.script_set_fingerprint == in_repo.script_set_fingerprint


def test_in_repo_experiments_remain_compatible(tmp_path: Path) -> None:
    """An experiment inside the apparatus repo still runs; workspace == apparatus there."""
    resolved = load_experiment(HARNESS_CHECK / "experiment.yaml")
    paths, rows = asyncio.run(run_experiment(resolved, results_root=tmp_path))
    assert len(rows) == 32
    apparatus_sha = apparatus_provenance()["source_commit_sha"]
    assert all(r.source_commit_sha == apparatus_sha for r in rows)
    assert all(r.workspace_commit_sha == apparatus_sha for r in rows)
    assert all(not Path(r.trace_path).is_absolute() for r in rows)
    assert (paths.root / rows[0].trace_path).is_file()
