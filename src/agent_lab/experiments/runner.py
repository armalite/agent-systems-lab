"""The agent loop and experiment execution.

The runner owns the loop: it builds each model request, asks the adapter for exactly one turn,
executes any requested tool calls over real MCP, appends the results, and repeats. Everything
observable is emitted as a trace event as it happens.

The runner computes no metrics. Results are derived afterwards, from the persisted trace only
(`SPEC.md` s18), so "the trace is authoritative" is enforced by construction rather than by
convention.
"""

import json
import subprocess
import time
from collections.abc import Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from mcp import Client
from pydantic import BaseModel, ConfigDict

import agent_lab as agent_lab_module
from agent_lab import __version__
from agent_lab.environments.loader import ConnectedEnvironment, connect_environment
from agent_lab.environments.surface import ModelSurface
from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.config import ResolvedExperiment
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, ResultRow, derive_result
from agent_lab.experiments.tasks import Task
from agent_lab.memory.resolve import ResolvedMemory, resolve_memory
from agent_lab.models.anthropic import AnthropicAdapter, exact_request_hash, redacted_request
from agent_lab.models.base import Message, ModelAdapter, ModelRequest, ProviderSurface
from agent_lab.models.fake import ScriptedAdapter, load_script_set
from agent_lab.models.provider import (
    PaidExecutionGate,
    ProviderCallError,
    RequestBudgetExceededError,
)
from agent_lab.storage.parquet import write_results
from agent_lab.tracing import events as ev
from agent_lab.tracing.recorder import TraceRecorder

STOP_ANSWERED = "answered"
STOP_MAX_STEPS = "max_steps"
STOP_NO_ANSWER = "no_answer"
STOP_PROVIDER_ERROR = "provider_error"


def build_adapter(resolved: ResolvedExperiment, gate: PaidExecutionGate) -> ModelAdapter:
    """Construct the configured adapter. Paid adapters are gated before any client is built."""
    config = resolved.config
    if config.adapter.kind == "scripted":
        assert config.adapter.script_set is not None
        return ScriptedAdapter(
            load_script_set(resolved.directory / config.adapter.script_set),
            model_name=config.model.name,
        )
    if config.adapter.kind == "anthropic":
        gate.authorize()
        return AnthropicAdapter(
            model=config.model.name,
            parameters=dict(config.model.parameters),
            gate=gate,
        )
    raise ValueError(f"unknown adapter kind {config.adapter.kind!r}")


@dataclass(frozen=True)
class _PreparedCondition:
    """Everything a condition needs, resolved once and reused across its scheduled runs."""

    env: ConnectedEnvironment
    surface: ModelSurface
    environment_fingerprint: str
    model_surface_fingerprint: str
    provider_surface: ProviderSurface | None
    provider_surface_fingerprint: str


@dataclass(frozen=True)
class ExecutionPaths:
    root: Path
    traces: Path
    environments: Path
    manifest: Path
    resolved_config: Path
    results: Path


def build_execution_id(started: datetime, existing: Path) -> str:
    """Physical execution identity: distinct per invocation so reruns never overwrite.

    A timestamp alone is not sufficient - two executions can start within the same second - so a
    deterministic counter is appended until the directory is free. Evidence is never clobbered.
    """
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    candidate = stamp
    suffix = 2
    while (existing / candidate).exists():
        candidate = f"{stamp}-{suffix}"
        suffix += 1
    return candidate


def build_run_id(experiment_id: str, tool_space_id: str, task_id: str, repetition: int) -> str:
    """Stable logical run identity, shared by every physical execution of the same cell."""
    return f"{experiment_id}/{tool_space_id}/{task_id}/r{repetition}"


class ScheduleEntry(BaseModel):
    """One cell of the frozen execution order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schedule_index: int
    repetition: int
    task_index: int
    task_id: str
    tool_space_id: str


def build_schedule(
    conditions: Sequence[str], task_ids: Sequence[str], repetitions: int
) -> tuple[ScheduleEntry, ...]:
    """Deterministic pair-adjacent counterbalanced execution order (`SPEC.md` s14.1, v2.5).

    Execution order is experimental design. Running every baseline observation before every
    overlap observation would confound condition with time, provider state, and a mutable model
    alias. Instead, for each repetition the two conditions of a task run **adjacently**, and the
    within-pair order alternates on `(task_index + repetition) % 2` so neither condition is
    systematically first.

    No RNG and therefore no seed: the schedule is a pure function of the frozen task order and
    repetition count, which is stronger than a stored seed because it is reconstructible without
    persisting randomness. The realized schedule is persisted anyway, as evidence.

    With a number of conditions other than two, counterbalancing is undefined and the declared
    condition order is used as-is.
    """
    entries: list[ScheduleEntry] = []
    for repetition in range(repetitions):
        for task_index, task_id in enumerate(task_ids):
            if len(conditions) == 2:
                forward = (task_index + repetition) % 2 == 0
                ordered = tuple(conditions) if forward else tuple(reversed(conditions))
            else:
                ordered = tuple(conditions)
            for tool_space_id in ordered:
                entries.append(
                    ScheduleEntry(
                        schedule_index=len(entries),
                        repetition=repetition,
                        task_index=task_index,
                        task_id=task_id,
                        tool_space_id=tool_space_id,
                    )
                )
    return tuple(entries)


def _execution_paths(results_root: Path, experiment_id: str, execution_id: str) -> ExecutionPaths:
    root = results_root / experiment_id / execution_id
    return ExecutionPaths(
        root=root,
        traces=root / "traces",
        environments=root / "environments",
        manifest=root / "manifest.json",
        resolved_config=root / "resolved_config.json",
        results=root / "results.parquet",
    )


def _git(*args: str) -> str | None:
    """Run a git command, returning stripped stdout or None on any failure."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _git_toplevel(directory: Path) -> Path | None:
    """The Git worktree root containing `directory`, or None if it is not in one.

    Always `git -C <directory>`: never the process working directory. A path outside any
    repository yields None rather than silently resolving to wherever the caller happened to be
    standing (`SPEC.md` s12.1).
    """
    top = _git("git", "-C", str(directory), "rev-parse", "--show-toplevel")
    return Path(top) if top else None


@lru_cache(maxsize=1)
def apparatus_root() -> Path | None:
    """Git root of the Agent Systems Lab source tree that is actually executing.

    Resolved from the installed `agent_lab` package location, so apparatus provenance is
    identical no matter which directory the run was launched from - including from an external
    research workspace (`SPEC.md` s12.1, s18.1).
    """
    return _git_toplevel(Path(agent_lab_module.__file__).resolve().parent)


def _provenance_at(root: Path | None, sha_key: str, dirty_key: str) -> dict[str, Any]:
    """Commit SHA and dirty state for one Git worktree, or explicit nulls when there is none."""
    if root is None:
        return {sha_key: None, dirty_key: None}
    sha = _git("git", "-C", str(root), "rev-parse", "HEAD")
    status = _git("git", "-C", str(root), "status", "--porcelain")
    return {
        sha_key: sha,
        dirty_key: None if status is None else bool(status.strip()),
    }


def apparatus_provenance() -> dict[str, Any]:
    """`source_*` describes the apparatus source tree only, never the caller's CWD."""
    return _provenance_at(apparatus_root(), "source_commit_sha", "source_tree_dirty")


def workspace_provenance(experiment_directory: Path) -> dict[str, Any]:
    """`workspace_*` describes the worktree holding the experiment definition.

    An experiment may sit several directories deep inside a research workspace, so the Git
    top-level is resolved from the experiment's own directory. An experiment outside any
    repository yields explicit nulls - never a CWD fallback.
    """
    return _provenance_at(
        _git_toplevel(experiment_directory), "workspace_commit_sha", "workspace_tree_dirty"
    )


def apparatus_lockfile_hash() -> str | None:
    """Dependency provenance for the apparatus, resolved from the apparatus root.

    Read relative to the process CWD this returned nothing whenever the harness was driven from
    anywhere but its own checkout, silently dropping dependency provenance.
    """
    from hashlib import sha256

    root = apparatus_root()
    if root is None:
        return None
    lock = root / "uv.lock"
    if not lock.exists():
        return None
    return "sha256:" + sha256(lock.read_bytes()).hexdigest()


async def _execute_tool_call(
    client: Client, name: str, arguments: dict[str, Any], available: frozenset[str]
) -> tuple[dict[str, Any] | None, str | None, str, float]:
    """Dispatch one tool call. Returns (structured result, error kind, detail, latency ms).

    A tool absent from the tool-space is not dispatched: that is a model error, distinguishable
    in the trace from a transport failure.
    """
    started = time.perf_counter()
    if name not in available:
        latency = (time.perf_counter() - started) * 1000
        return None, "unknown_tool", f"tool {name!r} is not present in this tool-space", latency
    try:
        result = await client.call_tool(name, arguments)
    except Exception as exc:  # transport faults must be recorded as evidence, not raised
        latency = (time.perf_counter() - started) * 1000
        return None, "transport_error", f"{type(exc).__name__}: {exc}", latency
    latency = (time.perf_counter() - started) * 1000
    if result.is_error:
        detail = json.dumps([block.model_dump(mode="json") for block in result.content])
        return None, "tool_error", detail, latency
    return result.structured_content, None, "", latency


async def _run_single(
    *,
    adapter: ModelAdapter,
    client: Client,
    task: Task,
    surface: ModelSurface,
    recorder: TraceRecorder,
    max_steps: int,
    parameters: dict[str, Any],
    tool_space_id: str,
    memory_message: str | None = None,
) -> None:
    available = frozenset(surface.tool_names())
    rendered_tools = adapter.render_tools(surface)
    # `SPEC.md` s4.3.2 (v2.10): memory is a separate leading user-role message, never merged
    # into system instructions and never assembled inside a provider adapter. It stays at index
    # 0 for the whole run, so every subsequent turn replays the identical frozen surface. With
    # no memory the message list is exactly what it was before Milestone 5.
    messages: list[Message] = []
    if memory_message is not None:
        messages.append(Message(role="user", content=memory_message))
    messages.append(Message(role="user", content=task.prompt))
    final_text: str | None = None
    stop_reason = STOP_NO_ANSWER

    for step in range(max_steps):
        request = ModelRequest(
            system_instructions=surface.system_instructions,
            messages=tuple(messages),
            rendered_tools=rendered_tools,
            parameters=parameters,
            metadata={"task_id": task.id, "tool_space_id": tool_space_id, "step": step},
        )
        payload: dict[str, Any] = {
            "step": step,
            "system_instructions": request.system_instructions,
            "messages": [m.model_dump(mode="json") for m in request.messages],
            "rendered_tools": list(request.rendered_tools),
            "parameters": request.parameters,
        }
        build = getattr(adapter, "build_request", None)
        if build is not None:
            # The exact full request body is evidence (SPEC.md s9.2, v2.3): persist it verbatim
            # for every turn, after deterministic secret redaction.
            body = redacted_request(build(request))
            payload["provider_request"] = body
            payload["provider_request_hash"] = exact_request_hash(body)
        recorder.emit(ev.MODEL_REQUEST, "model", payload)

        started = time.perf_counter()
        try:
            response = await adapter.generate(request)
        except ProviderCallError as exc:
            recorder.emit(
                ev.PROVIDER_ERROR,
                "provider",
                {"step": step, "error_kind": exc.kind, "detail": exc.detail},
            )
            recorder.emit(
                ev.RUN_COMPLETED,
                "harness",
                {"stop_reason": STOP_PROVIDER_ERROR, "final_text": None},
            )
            return
        latency_ms = (time.perf_counter() - started) * 1000

        recorder.emit(
            ev.MODEL_RESPONSE,
            "model",
            {
                "step": step,
                "text": response.text,
                "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
                "usage": response.usage,
                "latency_ms": latency_ms,
                "provider_request_id": response.provider_request_id,
                "raw": response.raw,
                "provider_blocks": list(response.provider_blocks or ()),
            },
        )
        messages.append(
            Message(
                role="assistant",
                content={
                    "text": response.text,
                    "tool_calls": [c.model_dump(mode="json") for c in response.tool_calls],
                },
                # Opaque to the runner; replayed verbatim by the adapter that produced it.
                provider_blocks=response.provider_blocks,
            )
        )

        if not response.tool_calls:
            final_text = response.text
            stop_reason = STOP_ANSWERED if final_text is not None else STOP_NO_ANSWER
            break

        for call in response.tool_calls:
            recorder.emit(
                ev.TOOL_CALL_REQUESTED,
                "model",
                {
                    "step": step,
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                    "attributable_to_model": True,
                },
            )
            structured, error_kind, detail, tool_latency = await _execute_tool_call(
                client, call.name, call.arguments, available
            )
            if error_kind is None:
                recorder.emit(
                    ev.TOOL_CALL_EXECUTED,
                    "mcp",
                    {"call_id": call.call_id, "latency_ms": tool_latency, "dispatched": True},
                )
                recorder.emit(
                    ev.TOOL_RESULT_RETURNED,
                    "tool",
                    {"call_id": call.call_id, "structured_content": structured, "is_error": False},
                )
                observation: Any = structured
            else:
                recorder.emit(
                    ev.TOOL_CALL_FAILED,
                    "mcp",
                    {
                        "call_id": call.call_id,
                        "error_kind": error_kind,
                        "detail": detail,
                        "latency_ms": tool_latency,
                        "dispatched": error_kind != "unknown_tool",
                    },
                )
                observation = {"error": error_kind, "detail": detail}
            messages.append(
                Message(
                    role="tool",
                    content={
                        "call_id": call.call_id,
                        "name": call.name,
                        "result": observation,
                        "is_error": error_kind is not None,
                    },
                )
            )
    else:
        stop_reason = STOP_MAX_STEPS

    recorder.emit(
        ev.RUN_COMPLETED, "harness", {"stop_reason": stop_reason, "final_text": final_text}
    )


async def run_experiment(
    resolved: ResolvedExperiment,
    *,
    results_root: Path = Path("results"),
    allow_paid: bool = False,
) -> tuple[ExecutionPaths, tuple[ResultRow, ...]]:
    """Execute every condition x task x repetition cell and persist all evidence.

    `allow_paid` is the run-time authorization required before any cost-incurring provider call
    (`SPEC.md` s19). Configured credentials authorize nothing on their own.
    """
    config = resolved.config
    gate = PaidExecutionGate(
        provider=config.model.provider,
        authorized=allow_paid,
        max_requests=(config.cost_controls.max_provider_requests if config.cost_controls else None),
    )
    adapter: ModelAdapter = build_adapter(resolved, gate)
    metric_set = METRIC_DEFINITION_SETS[config.metric_definition_set]

    started_at = datetime.now(UTC)
    execution_id = build_execution_id(started_at, results_root / config.id)
    paths = _execution_paths(results_root, config.id, execution_id)
    paths.traces.mkdir(parents=True, exist_ok=True)
    paths.environments.mkdir(parents=True, exist_ok=True)

    rows: list[ResultRow] = []
    tasks: Sequence[Task] = resolved.selected_tasks()
    by_id = {task.id: task for task in tasks}

    # Execution order is experimental design (`SPEC.md` s14.1, v2.5): frozen before the run and
    # persisted as evidence, so condition is not confounded with time or provider state.
    schedule = build_schedule(config.conditions, [task.id for task in tasks], config.repetitions)

    # Both provenance domains are captured once, at execution start, and written into the
    # authoritative raw evidence; normalized rows derive them from there rather than having them
    # injected independently (`SPEC.md` s12.1). Apparatus and workspace are separate domains and
    # neither is inferred from the process working directory.
    provenance = {**apparatus_provenance(), **workspace_provenance(resolved.directory)}

    aborted_reason: str | None = None
    try:
        async with AsyncExitStack() as stack:
            prepared: dict[str, _PreparedCondition] = {}
            # Both environments stay open for the whole execution so the two conditions of a
            # task/repetition pair can run adjacently.
            for tool_space_id in config.conditions:
                env = await stack.enter_async_context(connect_environment(tool_space_id))
                descriptor = env.descriptor
                surface = descriptor.model_surface(config.controls.system_instructions)
                environment_fingerprint = descriptor.fingerprint()
                model_surface_fingerprint = surface.fingerprint()

                # Third representation: what the provider is actually told, after the adapter
                # re-serializes the canonical surface into its own format. Not assumed equal to
                # the model surface - the Anthropic tool schema has no output-schema field.
                provider_surface: ProviderSurface | None = None
                provider_surface_fingerprint = ""
                describe = getattr(adapter, "provider_surface", None)
                if describe is not None:
                    described = cast(ProviderSurface, describe(surface))
                    provider_surface = described
                    provider_surface_fingerprint = described.fingerprint()

                prepared[tool_space_id] = _PreparedCondition(
                    env=env,
                    surface=surface,
                    environment_fingerprint=environment_fingerprint,
                    model_surface_fingerprint=model_surface_fingerprint,
                    provider_surface=provider_surface,
                    provider_surface_fingerprint=provider_surface_fingerprint,
                )

                (paths.environments / f"{tool_space_id}.json").write_text(
                    json.dumps(
                        {
                            "descriptor": descriptor.model_dump(mode="json"),
                            "environment_fingerprint": environment_fingerprint,
                            "model_surface": surface.model_dump(mode="json"),
                            "model_surface_fingerprint": model_surface_fingerprint,
                            "provider_surface": (
                                provider_surface.model_dump(mode="json")
                                if provider_surface
                                else None
                            ),
                            "provider_surface_fingerprint": provider_surface_fingerprint,
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            for entry in schedule:
                condition = prepared[entry.tool_space_id]
                task = by_id[entry.task_id]
                run_id = build_run_id(
                    config.id, entry.tool_space_id, entry.task_id, entry.repetition
                )
                context = {
                    "run_id": run_id,
                    "execution_id": execution_id,
                    "experiment_id": config.id,
                    "task_id": entry.task_id,
                    "repetition": entry.repetition,
                    "tool_space_id": entry.tool_space_id,
                    "environment_fingerprint": condition.environment_fingerprint,
                    "model_surface_fingerprint": condition.model_surface_fingerprint,
                    "provider_surface_fingerprint": condition.provider_surface_fingerprint,
                    "provider": adapter.provider,
                    "model": adapter.model,
                }
                trace_file = paths.traces / f"{run_id.replace('/', '__')}.jsonl"
                # Persisted as execution-root-relative so an external --results-root never puts
                # a developer-machine absolute path into normalized evidence (`SPEC.md` s13, v2.7).
                trace_reference = trace_file.relative_to(paths.root)
                with TraceRecorder(trace_file, context) as recorder:
                    recorder.emit(
                        ev.RUN_STARTED,
                        "harness",
                        {
                            "task": task.model_dump(mode="json"),
                            "config_fingerprint": resolved.config_fingerprint,
                            "task_set_fingerprint": resolved.task_set_fingerprint,
                            "script_set_fingerprint": resolved.script_set_fingerprint,
                            "controls": config.controls.model_dump(mode="json"),
                            "harness_version": __version__,
                            "schedule_index": entry.schedule_index,
                            "task_index": entry.task_index,
                            **provenance,
                        },
                    )
                    recorder.emit(
                        ev.ENVIRONMENT_CONNECTED,
                        "mcp",
                        {
                            "descriptor": condition.env.descriptor.model_dump(mode="json"),
                            "environment_fingerprint": condition.environment_fingerprint,
                            "model_surface_fingerprint": condition.model_surface_fingerprint,
                        },
                    )
                    if condition.provider_surface is not None:
                        recorder.emit(
                            ev.PROVIDER_SURFACE_PREPARED,
                            "provider",
                            {
                                "provider_surface": condition.provider_surface.model_dump(
                                    mode="json"
                                ),
                                "provider_surface_fingerprint": (
                                    condition.provider_surface_fingerprint
                                ),
                                "dropped_from_model_surface": [
                                    "title",
                                    "output_schema",
                                    "annotations",
                                ],
                            },
                        )
                    # Resolved once per run, before the first model request, and frozen for
                    # the rest of the run (`SPEC.md` s4.3.2). No memory configured emits no
                    # event at all, which is what makes the two empty states distinguishable.
                    resolved_memory: ResolvedMemory | None = None
                    if resolved.memory is not None:
                        resolved_memory = resolve_memory(resolved.memory)
                        recorder.emit(
                            ev.MEMORY_SURFACE_RESOLVED,
                            "harness",
                            resolved_memory.trace_payload(),
                        )
                    await _run_single(
                        adapter=adapter,
                        client=condition.env.client,
                        task=task,
                        surface=condition.surface,
                        recorder=recorder,
                        max_steps=config.controls.max_steps,
                        parameters=config.model.parameters,
                        tool_space_id=entry.tool_space_id,
                        memory_message=(
                            resolved_memory.rendered_message if resolved_memory else None
                        ),
                    )
                    # Derived strictly from the events emitted above.
                    row = derive_result(
                        events=recorder.events,
                        task=task,
                        resolved=resolved,
                        metric_set=metric_set,
                        trace_path=trace_reference,
                    )
                    recorder.emit(
                        ev.EVALUATION_COMPLETED,
                        "evaluator",
                        {**metric_set.provenance(), "metrics": row.metric_payload()},
                    )
                rows.append(row)

    except RequestBudgetExceededError as exc:
        # Persist everything gathered so far, then surface the abort. Evidence already paid for
        # is never discarded (SPEC.md s18).
        aborted_reason = str(exc)

    paths.resolved_config.write_text(
        json.dumps(
            {
                "config": config.model_dump(mode="json"),
                "config_fingerprint": resolved.config_fingerprint,
                "task_set_fingerprint": resolved.task_set_fingerprint,
                "script_set_fingerprint": resolved.script_set_fingerprint,
                "task_set": resolved.task_set.model_dump(mode="json"),
                "memory": (
                    {
                        "descriptor": resolved.memory.descriptor.canonical_form(),
                        "policy": resolved.memory.policy.canonical_form(),
                        "presentation_id": resolved.memory.presentation.id,
                        **resolved.memory.fingerprints(),
                    }
                    if resolved.memory is not None
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_results(paths.results, rows)
    paths.manifest.write_text(
        json.dumps(
            {
                "execution_id": execution_id,
                "experiment_id": config.id,
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "harness_version": __version__,
                "trace_schema_version": ev.TRACE_SCHEMA_VERSION,
                "result_schema_version": RESULT_SCHEMA_VERSION,
                "config_fingerprint": resolved.config_fingerprint,
                "task_set_fingerprint": resolved.task_set_fingerprint,
                "script_set_fingerprint": resolved.script_set_fingerprint,
                **(resolved.memory.fingerprints() if resolved.memory is not None else {}),
                **metric_set.provenance(),
                "lockfile_hash": apparatus_lockfile_hash(),
                **provenance,
                "run_count": len(rows),
                "conditions": list(config.conditions),
                "adapter_kind": config.adapter.kind,
                "model_requested": config.model.name,
                "model_controls": config.model.parameters,
                "model_snapshot_available": False if gate.is_paid else None,
                "provider_requests_used": gate.requests_used,
                "provider_request_budget": gate.max_requests,
                "paid_execution_authorized": allow_paid and gate.is_paid,
                "aborted": aborted_reason is not None,
                "aborted_reason": aborted_reason,
                "schedule_rule": (
                    "pair-adjacent counterbalanced; within-pair order alternates on "
                    "(task_index + repetition) % 2; deterministic, no RNG"
                ),
                "schedule": [entry.model_dump(mode="json") for entry in schedule],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    if aborted_reason is not None:
        raise RequestBudgetExceededError(aborted_reason)
    return paths, tuple(rows)
