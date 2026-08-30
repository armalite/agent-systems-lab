"""Milestone 1 acceptance: every tool invoked through the real MCP stdio path.

These tests launch the synthetic server as an actual subprocess and speak the real protocol -
no in-process shortcut - because the point of the milestone is that the environment works as an
MCP environment, not merely as Python functions.
"""

import asyncio
import json
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from agent_lab.mcp.client import canonical_tool_surface, synthetic_stdio_client
from agent_lab.synthetic.toolspaces import (
    BASELINE_TOOL_SPACE,
    OVERLAP_TOOL_SPACE,
    TOOL_SPACES,
)
from tests.calls import VALID_CALLS

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


async def _collect(tool_space: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One session per tool-space: list the surface and call every tool it exposes."""
    async with synthetic_stdio_client(tool_space) as client:
        surface = canonical_tool_surface((await client.list_tools()).tools)
        results: dict[str, Any] = {}
        for name in TOOL_SPACES[tool_space]:
            result = await client.call_tool(name, VALID_CALLS[name])
            results[name] = {
                "is_error": result.is_error,
                "structured_content": result.structured_content,
            }
        return surface, results


@cache
def _session(tool_space: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return asyncio.run(_collect(tool_space))


@pytest.mark.parametrize("tool_space", [BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE])
def test_tools_list_matches_the_declared_tool_space(tool_space: str) -> None:
    """The protocol surface itself differs between conditions - not a harness-side filter."""
    surface, _ = _session(tool_space)
    assert [tool["name"] for tool in surface] == sorted(TOOL_SPACES[tool_space])


def test_baseline_surface_excludes_the_overlap_tools() -> None:
    baseline, _ = _session(BASELINE_TOOL_SPACE)
    overlap, _ = _session(OVERLAP_TOOL_SPACE)
    baseline_names = {tool["name"] for tool in baseline}
    overlap_names = {tool["name"] for tool in overlap}
    assert len(baseline_names) == 5
    assert len(overlap_names) == 10
    assert baseline_names < overlap_names


@pytest.mark.parametrize("tool_space", [BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE])
def test_every_tool_is_callable_over_stdio_and_returns_fixture_data(tool_space: str) -> None:
    _, results = _session(tool_space)
    assert set(results) == set(TOOL_SPACES[tool_space])
    for name, result in results.items():
        assert result["is_error"] is False, f"{name} errored over MCP"
        payload = result["structured_content"]
        assert payload is not None, f"{name} returned no structured content"
        if "found" in payload:
            assert payload["found"] is True, f"{name} did not find its fixture record"
        else:
            assert payload["match_count"] >= 1


def test_mcp_results_match_direct_calls() -> None:
    """The protocol adapter must not transform the deterministic layer's answers."""
    from agent_lab.synthetic.toolspaces import TOOL_DEFINITIONS

    _, results = _session(OVERLAP_TOOL_SPACE)
    for name, result in results.items():
        direct = TOOL_DEFINITIONS[name].fn(**VALID_CALLS[name])
        assert result["structured_content"] == json.loads(direct.model_dump_json()), name


def test_repeated_calls_over_mcp_are_identical() -> None:
    """Determinism must survive the transport, including a fresh server subprocess."""
    first = _session(OVERLAP_TOOL_SPACE)[1]
    second = asyncio.run(_collect(OVERLAP_TOOL_SPACE))[1]
    assert first == second


def test_a_miss_is_a_structured_result_not_a_protocol_error() -> None:
    """Keeps "not found" distinguishable from transport failure once tracing exists."""

    async def go() -> Any:
        async with synthetic_stdio_client(BASELINE_TOOL_SPACE) as client:
            return await client.call_tool("get_customer", {"customer_id": "C999"})

    result = asyncio.run(go())
    assert result.is_error is False
    assert result.structured_content["found"] is False


@pytest.mark.parametrize("tool_space", [BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE])
def test_tool_surface_matches_snapshot(tool_space: str) -> None:
    """Pin the model-visible capability surface.

    Tool names, descriptions, and schemas are controlled experimental material: an unnoticed
    edit is a silent change to a control (AGENTS.md s5). This snapshot makes any such change
    surface as a reviewable diff. Regenerate deliberately with::

        uv run python -m tests.regenerate_snapshots
    """
    surface, _ = _session(tool_space)
    expected = json.loads((SNAPSHOT_DIR / f"tool_surface_{tool_space}.json").read_text())
    assert surface == expected


# Research-design vocabulary that must never reach the model (SPEC.md s6.13, s9.4). The MCP
# protocol's own `experimental` capability flag is excluded: it is protocol boilerplate, not
# content authored here.
DESIGN_VOCABULARY = (
    "overlap",
    "alias",
    "baseline",
    "calibration",
    "experiment",
    "condition",
    "fixture",
    "synthetic",
    "research",
    "hypothesis",
    "agent-lab",
    "agent_lab",
)


@pytest.mark.parametrize("tool_space", [BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE])
def test_tool_surface_carries_no_experimental_design_metadata(tool_space: str) -> None:
    """The model must not be able to see how the environment was constructed."""
    blob = json.dumps(_session(tool_space)[0]).casefold()
    for leaked in DESIGN_VOCABULARY:
        assert leaked not in blob, f"{leaked!r} leaked into the tool surface"


@pytest.mark.parametrize("tool_space", [BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE])
def test_server_identity_carries_no_experimental_design_metadata(tool_space: str) -> None:
    """Server identity and instructions are MCP-visible too, not just tool definitions.

    A model that can tell it is inside experimental apparatus is not being observed under the
    conditions we intend to measure, so the environment must not announce itself as one.
    """

    async def go() -> dict[str, Any]:
        async with synthetic_stdio_client(tool_space) as client:
            info = client.server_info
            return {
                "server_info": info.model_dump(mode="json") if info else None,
                "instructions": client.instructions,
            }

    identity = asyncio.run(go())
    blob = json.dumps(identity).casefold()
    for leaked in DESIGN_VOCABULARY:
        assert leaked not in blob, f"{leaked!r} leaked into server identity: {identity}"


def test_tool_space_identifiers_are_never_exposed_over_mcp() -> None:
    """`customer_baseline_v1` / `customer_overlap_v1` are internal condition labels."""

    async def go() -> str:
        async with synthetic_stdio_client(OVERLAP_TOOL_SPACE) as client:
            info = client.server_info
            return json.dumps(
                {
                    "server_info": info.model_dump(mode="json") if info else None,
                    "instructions": client.instructions,
                    "tools": canonical_tool_surface((await client.list_tools()).tools),
                }
            ).casefold()

    blob = asyncio.run(go())
    for tool_space in TOOL_SPACES:
        assert tool_space.casefold() not in blob
