"""Fingerprint semantics: the environment descriptor and the model surface are distinct.

`SPEC.md` s9.2 (v2.2) forbids equating MCP-client-visible metadata with model-visible context.
`serverInfo` is observed by the harness but is not put in the model request, so it must move the
environment fingerprint and leave the model-surface fingerprint alone.
"""

import asyncio

from agent_lab.environments.loader import connect_environment
from agent_lab.environments.surface import (
    EnvironmentDescriptor,
    ServerIdentity,
    fingerprint,
)

SYSTEM = "You are a helpful assistant."


def _descriptor(tool_space: str) -> EnvironmentDescriptor:
    async def go() -> EnvironmentDescriptor:
        async with connect_environment(tool_space) as env:
            return env.descriptor

    return asyncio.run(go())


def test_fingerprint_is_algorithm_tagged() -> None:
    assert fingerprint({"a": 1}).startswith("fp1:sha256:")


def test_fingerprint_is_key_order_insensitive() -> None:
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_baseline_and_overlap_have_different_fingerprints() -> None:
    baseline = _descriptor("customer_baseline_v1")
    overlap = _descriptor("customer_overlap_v1")
    assert baseline.fingerprint() != overlap.fingerprint()
    assert (
        baseline.model_surface(SYSTEM).fingerprint() != overlap.model_surface(SYSTEM).fingerprint()
    )


def test_fingerprints_are_stable_across_connections() -> None:
    first = _descriptor("customer_baseline_v1")
    second = _descriptor("customer_baseline_v1")
    assert first.fingerprint() == second.fingerprint()
    assert first.model_surface(SYSTEM).fingerprint() == second.model_surface(SYSTEM).fingerprint()


def test_server_identity_moves_environment_fingerprint_only() -> None:
    """The v2.2 acceptance criterion, stated as a test.

    Renaming the MCP server changes the environment the harness observes but changes nothing the
    model receives, so the model-surface fingerprint must not move.
    """
    original = _descriptor("customer_baseline_v1")
    renamed = original.model_copy(
        update={
            "server": ServerIdentity(
                name="something-else", title=None, version="9.9.9", description=None
            )
        }
    )
    assert renamed.fingerprint() != original.fingerprint()
    assert (
        renamed.model_surface(SYSTEM).fingerprint() == original.model_surface(SYSTEM).fingerprint()
    )


def test_server_instructions_move_environment_fingerprint_only() -> None:
    """Server instructions are model-visible only if the harness forwards them. It does not."""
    original = _descriptor("customer_baseline_v1")
    changed = original.model_copy(update={"server_instructions": "Prefer the newest tool."})
    assert changed.fingerprint() != original.fingerprint()
    assert (
        changed.model_surface(SYSTEM).fingerprint() == original.model_surface(SYSTEM).fingerprint()
    )


def test_observed_context_is_recorded_but_not_fingerprinted() -> None:
    """An SDK or protocol upgrade must not masquerade as an environment change."""
    original = _descriptor("customer_baseline_v1")
    assert "protocol_version" in original.observed_context
    bumped = original.model_copy(update={"observed_context": {"protocol_version": "9999-01-01"}})
    assert bumped.fingerprint() == original.fingerprint()


def test_tool_description_change_moves_both_fingerprints() -> None:
    """A description reaches the model, so it is experimental material in both views."""
    original = _descriptor("customer_baseline_v1")
    tools = list(original.tools)
    tools[0] = tools[0].model_copy(update={"description": "A different description."})
    changed = original.model_copy(update={"tools": tuple(tools)})
    assert changed.fingerprint() != original.fingerprint()
    assert (
        changed.model_surface(SYSTEM).fingerprint() != original.model_surface(SYSTEM).fingerprint()
    )


def test_system_instructions_are_part_of_the_model_surface() -> None:
    descriptor = _descriptor("customer_baseline_v1")
    a = descriptor.model_surface("You are a helpful assistant.").fingerprint()
    b = descriptor.model_surface("You are a terse assistant.").fingerprint()
    assert a != b
    assert descriptor.fingerprint() == descriptor.fingerprint()


def test_tool_ordering_does_not_affect_fingerprints() -> None:
    descriptor = _descriptor("customer_overlap_v1")
    reversed_tools = descriptor.model_copy(update={"tools": tuple(reversed(descriptor.tools))})
    assert reversed_tools.fingerprint() == descriptor.fingerprint()
    assert (
        reversed_tools.model_surface(SYSTEM).fingerprint()
        == descriptor.model_surface(SYSTEM).fingerprint()
    )


def test_model_surface_excludes_environment_only_metadata() -> None:
    descriptor = _descriptor("customer_baseline_v1")
    surface = descriptor.model_surface(SYSTEM)
    keys = set(surface.canonical_form())
    assert keys == {"system_instructions", "tools"}
    assert "server" not in keys
    assert "capabilities" not in keys
