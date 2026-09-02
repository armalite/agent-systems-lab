# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
#
# pyarrow ships no type information, so iterating RESULT_SCHEMA's fields is Unknown to a strict
# checker. Scoped as in storage/parquet.py and test_external_workspace.py.
"""Milestone 5 acceptance: controlled procedural memory as an auditable surface.

Structured against `SPEC.md` s4.3.2 (v2.10). The load-bearing checks audit the **persisted
provider request**, not the code that builds it - the O-001/O-002 lesson applies unchanged to
memory, which is now another way for design material to reach the model.

Nothing here touches a network or a paid provider: the scripted adapter covers the harness path
and an offline double covers the Anthropic request body.
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

import agent_lab.experiments.runner as runner_module
from agent_lab.evals.metrics import METRIC_DEFINITION_SETS
from agent_lab.experiments.config import ExperimentConfig, load_experiment
from agent_lab.experiments.result import RESULT_SCHEMA_VERSION, ResultRow, derive_result
from agent_lab.experiments.runner import ExecutionPaths, run_experiment
from agent_lab.memory import (
    ACTIVE_DECLARED_ORDER_V1,
    LEADING_USER_MEMORY_V1,
    DeclaredMemory,
    MemoryDescriptor,
    MemoryEntry,
    build_policy,
    build_presentation,
    load_memory_descriptor,
    resolve_memory,
)
from agent_lab.models.anthropic import AnthropicAdapter
from agent_lab.models.provider import PaidExecutionGate
from agent_lab.storage.parquet import RESULT_SCHEMA, read_results
from agent_lab.tracing import events as ev
from agent_lab.tracing.recorder import read_trace
from tests.anthropic_doubles import build_message, text_block, tool_use_block
from tests.test_external_workspace import make_workspace
from tests.test_mcp_server import DESIGN_VOCABULARY

# ------------------------------------------------------------------ declared material

ACTIVE_ONE = "When a question names a customer identifier, look that customer up before answering."
ACTIVE_TWO = "Identifiers are case-sensitive and should be passed exactly as they appear."
WITHDRAWN = "Order identifiers always begin with the letter O."

# Distinctive tokens: every one is hidden provenance and must never reach a provider request.
HIDDEN_TOKENS = (
    "m-yankee-1",
    "m-yankee-2",
    "m-yankee-3",
    "trace-zulu-77",
    "trace-zulu-78",
    "derivation-quebec-9",
    "fp1:sha256:" + "ab" * 32,
    "hand_authored_control",
    "trace_derived",
    "lifecycle_state",
    "inactive",
    "memory_id",
    "capability_dependencies",
    ACTIVE_DECLARED_ORDER_V1,
    LEADING_USER_MEMORY_V1,
)

CORPUS: dict[str, Any] = {
    "id": "memory_check_corpus_v1",
    "version": "1.0.0",
    "entries": [
        {
            "memory_id": "m-yankee-1",
            "model_visible_content": ACTIVE_ONE,
            "origin_type": "hand_authored_control",
            "lifecycle_state": "active",
            "capability_dependencies": ["get_customer"],
        },
        {
            "memory_id": "m-yankee-2",
            "model_visible_content": ACTIVE_TWO,
            "origin_type": "trace_derived",
            "lifecycle_state": "active",
            "source_trace_ids": ["trace-zulu-77", "trace-zulu-78"],
            "derivation_identity": "derivation-quebec-9",
            "learned_under_environment_fingerprint": "fp1:sha256:" + "ab" * 32,
            "learned_under_model_surface_fingerprint": "fp1:sha256:" + "cd" * 32,
        },
        {
            "memory_id": "m-yankee-3",
            "model_visible_content": WITHDRAWN,
            "origin_type": "hand_authored_control",
            "lifecycle_state": "inactive",
        },
    ],
}

MEMORY_BLOCK = {
    "entries": "memory.yaml",
    "policy": {"id": ACTIVE_DECLARED_ORDER_V1, "parameters": {}},
    "presentation": LEADING_USER_MEMORY_V1,
}

SMOKE = Path("experiments/smoke_anthropic").resolve()


def write_corpus(directory: Path, corpus: dict[str, Any]) -> Path:
    path = directory / "memory.yaml"
    path.write_text(yaml.safe_dump(corpus, sort_keys=False), encoding="utf-8")
    return path


def scripted_workspace(
    root: Path, *, corpus: dict[str, Any] | None = CORPUS, max_tasks: int = 2
) -> Path:
    """A throwaway research workspace whose experiment declares memory."""
    experiment_dir = make_workspace(root, commit=False)
    raw = yaml.safe_load((experiment_dir / "experiment.yaml").read_text())
    raw["limits"] = {"max_tasks": max_tasks}
    if corpus is not None:
        write_corpus(experiment_dir, corpus)
        raw["memory"] = MEMORY_BLOCK
    (experiment_dir / "experiment.yaml").write_text(yaml.safe_dump(raw, sort_keys=False))
    return experiment_dir


def declared(corpus: dict[str, Any] = CORPUS) -> DeclaredMemory:
    return DeclaredMemory(
        descriptor=MemoryDescriptor.model_validate(corpus),
        policy=build_policy(ACTIVE_DECLARED_ORDER_V1),
        presentation=build_presentation(LEADING_USER_MEMORY_V1),
    )


def mutated(**entry_changes: Any) -> dict[str, Any]:
    """CORPUS with the first entry's fields overridden."""
    corpus = json.loads(json.dumps(CORPUS))
    corpus["entries"][0].update(entry_changes)
    return cast(dict[str, Any], corpus)


# ------------------------------------------------------------------ 1. stable identity


def test_same_material_fingerprints_identically_from_any_location(tmp_path: Path) -> None:
    """Acceptance 1: identity is content, never filesystem location."""
    fingerprints: set[str] = set()
    for name in ("alpha/deep/nested", "beta"):
        directory = tmp_path / name
        directory.mkdir(parents=True)
        fingerprints.add(load_memory_descriptor(write_corpus(directory, CORPUS)).fingerprint())
    assert len(fingerprints) == 1
    assert next(iter(fingerprints)) == declared().descriptor_fingerprint()


def test_fingerprints_are_stable_across_repeated_resolution() -> None:
    first, second = resolve_memory(declared()), resolve_memory(declared())
    assert first.surface.fingerprint() == second.surface.fingerprint()
    assert first.trace_payload() == second.trace_payload()


def test_the_three_memory_fingerprints_are_distinct() -> None:
    resolved = resolve_memory(declared())
    values = {
        resolved.declared.descriptor_fingerprint(),
        resolved.declared.policy_fingerprint(),
        resolved.surface.fingerprint(),
    }
    assert len(values) == 3
    assert all(value.startswith("fp1:sha256:") for value in values)


# ------------------------------------------------- 2/3/4. what moves which fingerprint


def test_changing_model_visible_content_moves_the_surface_fingerprint() -> None:
    """Acceptance 2."""
    baseline = resolve_memory(declared())
    changed = resolve_memory(declared(mutated(model_visible_content=ACTIVE_ONE + " Always.")))
    assert changed.surface.fingerprint() != baseline.surface.fingerprint()
    assert changed.declared.descriptor_fingerprint() != baseline.declared.descriptor_fingerprint()


def test_changing_order_moves_the_surface_fingerprint() -> None:
    """Acceptance 2: presentation order is model-visible, so reordering is a real change."""
    reordered = json.loads(json.dumps(CORPUS))
    entries = reordered["entries"]
    reordered["entries"] = [entries[1], entries[0], entries[2]]
    baseline, changed = resolve_memory(declared()), resolve_memory(declared(reordered))
    assert changed.surface.fingerprint() != baseline.surface.fingerprint()
    assert changed.declared.descriptor_fingerprint() != baseline.declared.descriptor_fingerprint()
    assert changed.active_entry_ids == ("m-yankee-2", "m-yankee-1")


def test_lifecycle_change_moves_descriptor_and_selection_but_leaks_nothing() -> None:
    """Acceptance 3: hidden metadata that controls selection is still hidden metadata."""
    baseline = resolve_memory(declared())
    changed = resolve_memory(declared(mutated(lifecycle_state="inactive")))
    assert changed.declared.descriptor_fingerprint() != baseline.declared.descriptor_fingerprint()
    assert changed.active_entry_ids == ("m-yankee-2",)
    assert ACTIVE_ONE not in str(changed.surface.rendered_message)
    for token in ("lifecycle", "inactive", "active"):
        assert token not in str(changed.surface.rendered_message)


def test_provenance_only_metadata_does_not_move_the_surface_fingerprint() -> None:
    """Acceptance 4: the surface must not falsely change when nothing model-visible changed."""
    baseline = resolve_memory(declared())
    changed = resolve_memory(
        declared(
            mutated(
                origin_type="transformed",
                source_trace_ids=["trace-zulu-77"],
                derivation_identity="derivation-quebec-9",
                capability_dependencies=["get_customer", "get_order"],
            )
        )
    )
    assert changed.surface.fingerprint() == baseline.surface.fingerprint()
    assert changed.surface.rendered_message == baseline.surface.rendered_message
    assert changed.declared.descriptor_fingerprint() != baseline.declared.descriptor_fingerprint()


def test_policy_fingerprint_identifies_the_definition_not_the_outcome() -> None:
    """Acceptance: `memory_policy_fingerprint` must not encode which entries were selected."""
    full = resolve_memory(declared())
    none_active = resolve_memory(
        declared(
            {
                **CORPUS,
                "entries": [
                    {**entry, "lifecycle_state": "inactive"} for entry in CORPUS["entries"]
                ],
            }
        )
    )
    assert full.declared.policy_fingerprint() == none_active.declared.policy_fingerprint()
    assert full.surface.fingerprint() != none_active.surface.fingerprint()


def test_policy_parameters_are_part_of_policy_identity() -> None:
    definition = build_policy(ACTIVE_DECLARED_ORDER_V1).definition
    with pytest.raises(ValueError, match="accepts no parameter"):
        build_policy(ACTIVE_DECLARED_ORDER_V1, {"max_entries": 2})
    assert definition.parameter_names == ()
    assert build_policy(ACTIVE_DECLARED_ORDER_V1).fingerprint().startswith("fp1:sha256:")


def test_unknown_policy_and_presentation_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown memory policy"):
        build_policy("recency_weighted_v1")
    with pytest.raises(ValueError, match="unknown memory presentation"):
        build_presentation("system_prompt_memory_v1")


# ------------------------------------------------------------------ declared material rules


def test_controlled_material_cannot_claim_to_be_learned_experience() -> None:
    """`SPEC.md` s4.3.1: synthetic material must never be presented as acquired experience."""
    with pytest.raises(ValueError, match="must not claim source traces"):
        MemoryEntry(
            memory_id="m",
            model_visible_content="x",
            origin_type="synthetic_control",
            lifecycle_state="active",
            source_trace_ids=("trace-zulu-77",),
        )


def test_trace_derived_material_must_name_its_evidence() -> None:
    with pytest.raises(ValueError, match="source traces"):
        MemoryEntry(
            memory_id="m",
            model_visible_content="x",
            origin_type="trace_derived",
            lifecycle_state="active",
        )
    with pytest.raises(ValueError, match="derivation_identity"):
        MemoryEntry(
            memory_id="m",
            model_visible_content="x",
            origin_type="trace_derived",
            lifecycle_state="active",
            source_trace_ids=("trace-zulu-77",),
        )


def test_duplicate_memory_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate memory ids"):
        MemoryDescriptor.model_validate(
            {
                "id": "dupes",
                "version": "1.0.0",
                "entries": [CORPUS["entries"][0], CORPUS["entries"][0]],
            }
        )


# ------------------------------------------------------------------ 6. rendering and placement


def test_rendered_message_is_the_wrapper_plus_ordered_content_and_nothing_else() -> None:
    surface = resolve_memory(declared()).surface
    assert surface.rendered_message == f"Notes:\n\n{ACTIVE_ONE}\n\n{ACTIVE_TWO}"
    assert surface.role == "user"
    assert surface.placement == "leading_message"
    assert WITHDRAWN not in str(surface.rendered_message)


def test_the_harness_authored_wrapper_carries_no_design_vocabulary() -> None:
    """Acceptance 11, scoped correctly: researcher-authored entry text is experimental material
    and may legitimately contain ordinary English. The wrapper the *harness* contributes may
    not."""
    definition = build_presentation(LEADING_USER_MEMORY_V1)
    wrapper = (definition.header + definition.entry_separator).casefold()
    for leaked in DESIGN_VOCABULARY:
        assert leaked not in wrapper


def test_the_wrapper_contains_no_ids_counts_or_lifecycle_labels() -> None:
    rendered = str(resolve_memory(declared()).surface.rendered_message)
    for token in HIDDEN_TOKENS:
        assert token not in rendered


# ------------------------------------------------------------------ scripted end-to-end


@pytest.fixture(scope="module")
def memory_execution(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[ExecutionPaths, tuple[ResultRow, ...], Path]:
    workspace = tmp_path_factory.mktemp("memory_ws")
    experiment_dir = scripted_workspace(workspace)
    resolved = load_experiment(experiment_dir / "experiment.yaml")
    paths, rows = asyncio.run(run_experiment(resolved, results_root=workspace / "results"))
    return paths, rows, experiment_dir


def test_memory_surface_resolved_precedes_the_first_model_request(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    """Acceptance 7: once per run, before the first request."""
    paths, _, _ = memory_execution
    for path in paths.traces.glob("*.jsonl"):
        types = [event.event_type for event in read_trace(path)]
        assert types.count(ev.MEMORY_SURFACE_RESOLVED) == 1
        assert types.index(ev.MEMORY_SURFACE_RESOLVED) < types.index(ev.MODEL_REQUEST)
        assert types.index(ev.RUN_STARTED) < types.index(ev.MEMORY_SURFACE_RESOLVED)


def test_the_resolution_event_is_self_contained_evidence(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    paths, _, _ = memory_execution
    event = next(
        e
        for e in read_trace(next(iter(paths.traces.glob("*.jsonl"))))
        if e.event_type == ev.MEMORY_SURFACE_RESOLVED
    )
    payload = event.payload
    assert event.layer == "harness"
    assert payload["active_entry_ids"] == ["m-yankee-1", "m-yankee-2"]
    assert payload["memory_entry_count"] == 2
    assert payload["declared_entry_count"] == 3
    assert payload["presentation_id"] == LEADING_USER_MEMORY_V1
    assert payload["placement"] == "leading_message"
    assert payload["message_inserted"] is True
    assert payload["rendered_message"].startswith("Notes:")
    # The full declared corpus, hidden provenance included, so selection is re-checkable from
    # the trace alone.
    declared_ids = [e["memory_id"] for e in payload["memory_descriptor"]["entries"]]
    assert declared_ids == ["m-yankee-1", "m-yankee-2", "m-yankee-3"]
    for key in (
        "memory_descriptor_fingerprint",
        "memory_policy_fingerprint",
        "memory_surface_fingerprint",
    ):
        assert payload[key].startswith("fp1:sha256:")


def test_the_frozen_surface_is_replayed_on_every_turn(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    """Acceptance 7: per-run selection, invariant across turns."""
    paths, _, _ = memory_execution
    multi_turn = 0
    for path in paths.traces.glob("*.jsonl"):
        events = read_trace(path)
        expected = next(e for e in events if e.event_type == ev.MEMORY_SURFACE_RESOLVED).payload[
            "rendered_message"
        ]
        requests = [e for e in events if e.event_type == ev.MODEL_REQUEST]
        multi_turn += len(requests) > 1
        for request in requests:
            leading = request.payload["messages"][0]
            assert leading["role"] == "user"
            assert leading["content"] == expected
    assert multi_turn, "no multi-turn run exercised replay"


def test_rows_and_parquet_carry_the_memory_identity(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    """Acceptance: concise derived fields, and DuckDB can see them."""
    paths, rows, _ = memory_execution
    expected = resolve_memory(declared()).result_fields()
    for row in rows:
        assert row.memory_descriptor_fingerprint == expected["memory_descriptor_fingerprint"]
        assert row.memory_policy_fingerprint == expected["memory_policy_fingerprint"]
        assert row.memory_surface_fingerprint == expected["memory_surface_fingerprint"]
        assert row.memory_entry_count == 2
        assert row.result_schema_version == RESULT_SCHEMA_VERSION == "1.4.0"

    names = {field.name for field in RESULT_SCHEMA}
    assert {
        "memory_descriptor_fingerprint",
        "memory_policy_fingerprint",
        "memory_surface_fingerprint",
        "memory_entry_count",
    } <= names
    records = read_results(paths.results)
    assert all(record["memory_entry_count"] == 2 for record in records)


def test_memory_fields_are_re_derivable_from_the_trace_alone(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    """Evidence authority: the derived row must be reproducible from the raw trace."""
    paths, rows, experiment_dir = memory_execution
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


def test_declared_memory_binds_into_the_config_fingerprint(tmp_path: Path) -> None:
    """Acceptance 10: external material is content-bound by the resolved experiment."""
    first = scripted_workspace(tmp_path / "a")
    second = scripted_workspace(tmp_path / "b")
    assert (
        load_experiment(first / "experiment.yaml").config_fingerprint
        == load_experiment(second / "experiment.yaml").config_fingerprint
    )
    write_corpus(second, mutated(model_visible_content="Something else entirely."))
    assert (
        load_experiment(first / "experiment.yaml").config_fingerprint
        != load_experiment(second / "experiment.yaml").config_fingerprint
    )


def test_hidden_provenance_alone_still_rebinds_the_experiment(tmp_path: Path) -> None:
    """Material with identical text but different provenance is a different input."""
    first = scripted_workspace(tmp_path / "a")
    second = scripted_workspace(tmp_path / "b")
    write_corpus(second, mutated(capability_dependencies=["get_customer", "get_order"]))
    one = load_experiment(first / "experiment.yaml")
    two = load_experiment(second / "experiment.yaml")
    assert one.config_fingerprint != two.config_fingerprint
    assert one.memory is not None and two.memory is not None
    assert resolve_memory(one.memory).surface.fingerprint() == (
        resolve_memory(two.memory).surface.fingerprint()
    )


def test_execution_artifacts_record_the_declared_corpus(
    memory_execution: tuple[ExecutionPaths, tuple[ResultRow, ...], Path],
) -> None:
    paths, _, _ = memory_execution
    config = json.loads(paths.resolved_config.read_text())
    assert config["memory"]["descriptor"]["memory_set_id"] == "memory_check_corpus_v1"
    manifest = json.loads(paths.manifest.read_text())
    assert manifest["memory_descriptor_fingerprint"].startswith("fp1:sha256:")
    assert manifest["memory_policy_fingerprint"].startswith("fp1:sha256:")


# ------------------------------------------------------------------ 5/9. the two empty states


def test_no_memory_configured_leaves_every_memory_field_null(tmp_path: Path) -> None:
    """Acceptance 5 and 9, first state."""
    experiment_dir = scripted_workspace(tmp_path, corpus=None)
    resolved = load_experiment(experiment_dir / "experiment.yaml")
    assert resolved.config.memory is None and resolved.memory is None
    paths, rows = asyncio.run(run_experiment(resolved, results_root=tmp_path / "results"))
    for row in rows:
        assert row.memory_descriptor_fingerprint is None
        assert row.memory_policy_fingerprint is None
        assert row.memory_surface_fingerprint is None
        assert row.memory_entry_count is None
    for path in paths.traces.glob("*.jsonl"):
        events = read_trace(path)
        assert not [e for e in events if e.event_type == ev.MEMORY_SURFACE_RESOLVED]
        for request in (e for e in events if e.event_type == ev.MODEL_REQUEST):
            assert len(request.payload["messages"]) >= 1
            assert request.payload["messages"][0]["content"].endswith("?")


def test_configured_but_empty_memory_is_a_distinct_recorded_state(tmp_path: Path) -> None:
    """Acceptance 9, second state: real identity, empty surface, no message."""
    all_inactive: dict[str, Any] = {
        **CORPUS,
        "entries": [{**entry, "lifecycle_state": "inactive"} for entry in CORPUS["entries"]],
    }
    experiment_dir = scripted_workspace(tmp_path, corpus=all_inactive)
    resolved = load_experiment(experiment_dir / "experiment.yaml")
    paths, rows = asyncio.run(run_experiment(resolved, results_root=tmp_path / "results"))

    for row in rows:
        assert row.memory_descriptor_fingerprint is not None
        assert row.memory_policy_fingerprint is not None
        assert row.memory_surface_fingerprint is not None
        assert row.memory_entry_count == 0

    for path in paths.traces.glob("*.jsonl"):
        events = read_trace(path)
        resolution = next(e for e in events if e.event_type == ev.MEMORY_SURFACE_RESOLVED)
        assert resolution.payload["active_entry_ids"] == []
        assert resolution.payload["rendered_message"] is None
        assert resolution.payload["message_inserted"] is False
        for request in (e for e in events if e.event_type == ev.MODEL_REQUEST):
            assert request.payload["messages"][0]["content"].endswith("?")


def test_the_empty_surface_fingerprint_is_canonical(tmp_path: Path) -> None:
    """The same empty surface regardless of which corpus produced it."""
    empty_corpus: dict[str, Any] = {"id": "other_corpus", "version": "9.9.9", "entries": []}
    all_inactive: dict[str, Any] = {
        **CORPUS,
        "entries": [{**entry, "lifecycle_state": "inactive"} for entry in CORPUS["entries"]],
    }
    one, two = resolve_memory(declared(empty_corpus)), resolve_memory(declared(all_inactive))
    assert one.surface.fingerprint() == two.surface.fingerprint()
    assert one.surface.rendered_message is None
    # Empty surface identity is not null identity: the descriptors still differ.
    assert one.declared.descriptor_fingerprint() != two.declared.descriptor_fingerprint()


def test_the_no_memory_path_is_byte_identical_to_pre_m5(tmp_path: Path) -> None:
    """The pre-M5 config fingerprint must survive: memory is absent, not null."""
    in_repo = load_experiment(Path("experiments/harness_check/experiment.yaml"))
    payload = json.loads(
        json.dumps(
            {
                "config": in_repo.config.model_dump(mode="json"),
                "task_set_fingerprint": in_repo.task_set_fingerprint,
                "script_set_fingerprint": in_repo.script_set_fingerprint,
            }
        )
    )
    assert "memory" in payload["config"]
    del payload["config"]["memory"]
    from agent_lab.environments.surface import fingerprint

    assert in_repo.config_fingerprint == fingerprint(payload)


def test_shipped_experiments_declare_no_memory() -> None:
    """M5 adds apparatus capability, not a study. Nothing shipped becomes memory-enabled."""
    for config in Path("experiments").glob("*/experiment.yaml"):
        raw = yaml.safe_load(config.read_text())
        assert ExperimentConfig.model_validate(raw).memory is None


# ------------------------------------------------------------------ 8/11. provider evidence


class _MemoryAwareFakeClient:
    """Answers one tool call then a text answer, reading the *task* prompt, not message 0."""

    def __init__(self) -> None:
        self.messages = self
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        conversation = kwargs["messages"]
        if any(message["role"] == "assistant" for message in conversation):
            return build_message(blocks=[text_block("The email address is a@example.test.")])
        prompt = str(conversation[-1]["content"])
        customer = "C102" if "C102" in prompt else "C104"
        return build_message(
            blocks=[tool_use_block("toolu_x", "get_customer", {"customer_id": customer})],
            stop_reason="tool_use",
        )


@pytest.fixture(scope="module")
def provider_execution(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[ExecutionPaths, _MemoryAwareFakeClient]:
    """The real M3 path with memory declared, and only the network replaced."""
    workspace = tmp_path_factory.mktemp("memory_provider")
    experiment_dir = workspace / "experiments" / "study"
    experiment_dir.mkdir(parents=True)
    for name in ("experiment.yaml", "tasks.yaml"):
        shutil.copy(SMOKE / name, experiment_dir / name)
    raw = yaml.safe_load((experiment_dir / "experiment.yaml").read_text())
    raw["limits"] = {"max_tasks": 1}
    raw["memory"] = MEMORY_BLOCK
    (experiment_dir / "experiment.yaml").write_text(yaml.safe_dump(raw, sort_keys=False))
    write_corpus(experiment_dir, CORPUS)

    client = _MemoryAwareFakeClient()
    resolved = load_experiment(experiment_dir / "experiment.yaml")

    def _fake_adapter(_r: Any, gate: PaidExecutionGate) -> AnthropicAdapter:
        gate.authorize()
        return AnthropicAdapter(
            model=resolved.config.model.name,
            parameters=dict(resolved.config.model.parameters),
            gate=gate,
            client=cast(Any, client),
        )

    original = runner_module.build_adapter
    runner_module.build_adapter = _fake_adapter
    try:
        paths, _ = asyncio.run(
            run_experiment(resolved, results_root=workspace / "results", allow_paid=True)
        )
    finally:
        runner_module.build_adapter = original
    return paths, client


def test_exact_provider_request_shows_the_memory_message_and_its_placement(
    provider_execution: tuple[ExecutionPaths, _MemoryAwareFakeClient],
) -> None:
    """Acceptance 8: the persisted request, not the code, is the evidence."""
    paths, _ = provider_execution
    expected = f"Notes:\n\n{ACTIVE_ONE}\n\n{ACTIVE_TWO}"
    seen = 0
    for path in paths.traces.glob("*.jsonl"):
        for event in read_trace(path):
            if event.event_type != ev.MODEL_REQUEST:
                continue
            body = event.payload["provider_request"]
            assert body["messages"][0] == {"role": "user", "content": expected}
            assert body["messages"][1]["role"] == "user"
            assert expected not in body["system"]
            seen += 1
    assert seen >= 2, "memory must be proved present on more than the first turn"


def test_memory_never_reaches_system_instructions_or_the_tool_surface(
    provider_execution: tuple[ExecutionPaths, _MemoryAwareFakeClient],
) -> None:
    """`SPEC.md` v2.10: the capability surface fingerprint must stay independent of memory."""
    paths, _ = provider_execution
    for path in paths.traces.glob("*.jsonl"):
        for event in read_trace(path):
            if event.event_type != ev.MODEL_REQUEST:
                continue
            body = event.payload["provider_request"]
            blob = json.dumps([body["system"], body["tools"]])
            for token in (ACTIVE_ONE, ACTIVE_TWO, "Notes:"):
                assert token not in blob


def test_hidden_provenance_never_reaches_the_provider(
    provider_execution: tuple[ExecutionPaths, _MemoryAwareFakeClient],
) -> None:
    """Acceptance 11, audited against the recorded request body."""
    paths, client = provider_execution
    bodies = [json.dumps(request, default=str) for request in client.requests]
    for path in paths.traces.glob("*.jsonl"):
        bodies += [
            json.dumps(event.payload["provider_request"])
            for event in read_trace(path)
            if event.event_type == ev.MODEL_REQUEST
        ]
    assert bodies
    for body in bodies:
        for token in HIDDEN_TOKENS:
            assert token not in body, f"{token!r} reached the provider"
        assert WITHDRAWN not in body, "an inactive entry was presented to the model"


def test_the_capability_surface_fingerprint_is_unmoved_by_memory(tmp_path: Path) -> None:
    """Memory must not be silently folded into `model_surface_fingerprint`."""
    with_memory = scripted_workspace(tmp_path / "with")
    without = scripted_workspace(tmp_path / "without", corpus=None)
    runs = [
        asyncio.run(
            run_experiment(
                load_experiment(directory / "experiment.yaml"),
                results_root=directory.parent / "results",
            )
        )[1]
        for directory in (with_memory, without)
    ]
    assert runs[0][0].model_surface_fingerprint == runs[1][0].model_surface_fingerprint
    assert runs[0][0].environment_fingerprint == runs[1][0].environment_fingerprint
    assert runs[0][0].memory_surface_fingerprint is not None
    assert runs[1][0].memory_surface_fingerprint is None


# ------------------------------------------------------------------ inspection ergonomics


def test_validate_reports_memory_identity_without_running_anything(tmp_path: Path) -> None:
    """The mandated post-M5 leakage inspection needs the resolved surface visible up front."""
    from typer.testing import CliRunner

    from agent_lab.cli import app

    experiment_dir = scripted_workspace(tmp_path)
    result = CliRunner().invoke(app, ["validate", str(experiment_dir / "experiment.yaml")])
    assert result.exit_code == 0, result.output
    assert "memory corpus         memory_check_corpus_v1" in result.output
    assert f"memory policy         {ACTIVE_DECLARED_ORDER_V1}" in result.output
    assert "memory entries        2 active of 3 declared" in result.output
    assert result.output.count("fp1:sha256:") >= 6


def test_validate_says_nothing_about_memory_when_none_is_declared() -> None:
    from typer.testing import CliRunner

    from agent_lab.cli import app

    result = CliRunner().invoke(app, ["validate", "experiments/harness_check/experiment.yaml"])
    assert result.exit_code == 0
    assert "memory" not in result.output
