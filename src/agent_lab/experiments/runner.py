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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from mcp import Client

from agent_lab import __version__
from agent_lab.environments.loader import connect_environment
from agent_lab.environments.surface import ModelSurface
from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.config import ResolvedExperiment
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, ResultRow, derive_result
from agent_lab.experiments.tasks import Task
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


def _git_provenance() -> dict[str, Any]:
    """Source identity, including whether the tree was dirty at execution time."""

    def _run(*args: str) -> str | None:
        try:
            done = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    sha = _run("git", "rev-parse", "HEAD")
    status = _run("git", "status", "--porcelain")
    return {
        "source_commit_sha": sha,
        "source_tree_dirty": None if status is None else bool(status.strip()),
    }


def _lockfile_hash() -> str | None:
    from hashlib import sha256

    lock = Path("uv.lock")
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
) -> None:
    available = frozenset(surface.tool_names())
    rendered_tools = adapter.render_tools(surface)
    messages: list[Message] = [Message(role="user", content=task.prompt)]
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

    aborted_reason: str | None = None
    try:
        for tool_space_id in config.conditions:
            async with connect_environment(tool_space_id) as env:
                descriptor = env.descriptor
                surface = descriptor.model_surface(config.controls.system_instructions)
                environment_fingerprint = descriptor.fingerprint()
                model_surface_fingerprint = surface.fingerprint()

                # Third representation: what the provider is actually told, after the adapter
                # re-serializes the canonical surface into its own format. Not assumed equal to the
                # model surface - the Anthropic tool schema has no output-schema field.
                provider_surface: ProviderSurface | None = None
                provider_surface_fingerprint = ""
                describe = getattr(adapter, "provider_surface", None)
                if describe is not None:
                    described = cast(ProviderSurface, describe(surface))
                    provider_surface = described
                    provider_surface_fingerprint = described.fingerprint()

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

                for task in tasks:
                    for repetition in range(config.repetitions):
                        run_id = build_run_id(config.id, tool_space_id, task.id, repetition)
                        context = {
                            "run_id": run_id,
                            "execution_id": execution_id,
                            "experiment_id": config.id,
                            "task_id": task.id,
                            "repetition": repetition,
                            "tool_space_id": tool_space_id,
                            "environment_fingerprint": environment_fingerprint,
                            "model_surface_fingerprint": model_surface_fingerprint,
                            "provider_surface_fingerprint": provider_surface_fingerprint,
                            "provider": adapter.provider,
                            "model": adapter.model,
                        }
                        trace_path = paths.traces / f"{run_id.replace('/', '__')}.jsonl"
                        with TraceRecorder(trace_path, context) as recorder:
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
                                },
                            )
                            recorder.emit(
                                ev.ENVIRONMENT_CONNECTED,
                                "mcp",
                                {
                                    "descriptor": descriptor.model_dump(mode="json"),
                                    "environment_fingerprint": environment_fingerprint,
                                    "model_surface_fingerprint": model_surface_fingerprint,
                                },
                            )
                            if provider_surface is not None:
                                recorder.emit(
                                    ev.PROVIDER_SURFACE_PREPARED,
                                    "provider",
                                    {
                                        "provider_surface": provider_surface.model_dump(
                                            mode="json"
                                        ),
                                        "provider_surface_fingerprint": (
                                            provider_surface_fingerprint
                                        ),
                                        "dropped_from_model_surface": [
                                            "title",
                                            "output_schema",
                                            "annotations",
                                        ],
                                    },
                                )
                            await _run_single(
                                adapter=adapter,
                                client=env.client,
                                task=task,
                                surface=surface,
                                recorder=recorder,
                                max_steps=config.controls.max_steps,
                                parameters=config.model.parameters,
                                tool_space_id=tool_space_id,
                            )
                            # Derived strictly from the events emitted above.
                            row = derive_result(
                                events=recorder.events,
                                task=task,
                                resolved=resolved,
                                metric_set=metric_set,
                                trace_path=trace_path,
                            )
                            recorder.emit(
                                ev.EVALUATION_COMPLETED,
                                "evaluator",
                                {
                                    **metric_set.provenance(),
                                    "metrics": row.metric_payload(),
                                },
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
                **metric_set.provenance(),
                "lockfile_hash": _lockfile_hash(),
                **_git_provenance(),
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
