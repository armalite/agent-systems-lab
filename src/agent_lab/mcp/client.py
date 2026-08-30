"""Minimal client helpers for talking to a synthetic environment over real MCP stdio.

Scope is deliberately small: connect, list the capability surface, call a tool. There is no
retry policy, no session pooling, and no transport abstraction layer - those belong to whichever
milestone genuinely needs them.

stdio is the Milestone 1 transport: no ports, no network stack, and no server lifecycle to
manage, which keeps transport noise out of an experiment whose only intended variable is the
tool-space.
"""

import sys
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp import Client, StdioServerParameters, Tool

SERVER_MODULE = "agent_lab.synthetic.server"


def stdio_parameters(tool_space: str) -> StdioServerParameters:
    """Launch parameters for the synthetic server exposing `tool_space`.

    Uses the current interpreter so the subprocess runs in the same environment as its caller.
    """
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE, "--tool-space", tool_space],
    )


@asynccontextmanager
async def synthetic_stdio_client(tool_space: str) -> AsyncGenerator[Client]:
    """Connect to the synthetic environment as a real MCP stdio subprocess."""
    async with Client(stdio_parameters(tool_space)) as client:
        yield client


def canonical_tool_surface(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """Reduce `tools/list` to the experimentally relevant, model-visible surface.

    Keeps name, title, description, and the input/output schemas - what actually reaches the
    model - and drops incidental SDK and protocol metadata, so a snapshot of this stays stable
    across SDK versions while still failing on any real change to the capability surface.

    Ordered by tool name, with schema keys sorted, so the representation is deterministic and
    independent of registration order.
    """

    def _sort(value: Any) -> Any:
        if isinstance(value, dict):
            mapping = cast(dict[str, Any], value)
            return {key: _sort(mapping[key]) for key in sorted(mapping)}
        if isinstance(value, list):
            return [_sort(item) for item in cast(list[Any], value)]
        return value

    return [
        {
            "name": tool.name,
            "title": tool.title,
            "description": tool.description,
            "input_schema": _sort(tool.input_schema),
            "output_schema": _sort(tool.output_schema),
        }
        for tool in sorted(tools, key=lambda tool: tool.name)
    ]
