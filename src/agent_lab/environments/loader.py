"""Connect to a synthetic MCP environment and capture its canonical identity."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp import Client

from agent_lab.environments.surface import (
    CanonicalTool,
    EnvironmentDescriptor,
    ServerIdentity,
)
from agent_lab.mcp.client import synthetic_stdio_client
from agent_lab.synthetic.server import SERVER_VERSION
from agent_lab.synthetic.toolspaces import TOOL_SPACES

ENVIRONMENT_ID = "customer_env"


@dataclass(frozen=True)
class ConnectedEnvironment:
    """A live MCP session plus the canonical description of what it exposes."""

    client: Client
    descriptor: EnvironmentDescriptor


async def describe_environment(client: Client, tool_space_id: str) -> EnvironmentDescriptor:
    """Build the canonical descriptor from a live session."""
    info = client.server_info
    capabilities = (
        client.server_capabilities.model_dump(mode="json") if client.server_capabilities else {}
    )
    tools = tuple(
        CanonicalTool(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            annotations=tool.annotations.model_dump(mode="json") if tool.annotations else None,
        )
        for tool in sorted((await client.list_tools()).tools, key=lambda t: t.name)
    )
    observed: dict[str, Any] = {"protocol_version": str(client.protocol_version)}
    return EnvironmentDescriptor(
        environment_id=ENVIRONMENT_ID,
        environment_version=SERVER_VERSION,
        tool_space_id=tool_space_id,
        server=ServerIdentity(
            name=info.name if info else "",
            title=info.title if info else None,
            version=info.version if info else None,
            description=info.description if info else None,
        ),
        server_instructions=client.instructions,
        capabilities=capabilities,
        tools=tools,
        observed_context=observed,
    )


@asynccontextmanager
async def connect_environment(tool_space_id: str) -> AsyncGenerator[ConnectedEnvironment]:
    """Open a real stdio MCP session for a named tool-space."""
    if tool_space_id not in TOOL_SPACES:
        raise KeyError(f"unknown tool-space {tool_space_id!r}; known: {tuple(sorted(TOOL_SPACES))}")
    async with synthetic_stdio_client(tool_space_id) as client:
        yield ConnectedEnvironment(
            client=client,
            descriptor=await describe_environment(client, tool_space_id),
        )
