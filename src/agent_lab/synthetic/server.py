"""MCP protocol adapter for the synthetic environment.

This module is deliberately thin: it registers the tool-space's callables with an `MCPServer`
and runs it over stdio. It contains no lookup logic, so anything that fails here is a protocol
or transport problem rather than an environment-behaviour problem.

The exposed surface is selected server-side at launch, so the real `tools/list` response
differs between conditions - the model sees the manipulated variable through the protocol
itself rather than through harness-side filtering.

Run as::

    python -m agent_lab.synthetic.server --tool-space customer_baseline_v1

Nothing may be written to stdout: under the stdio transport, stdout carries the protocol.
"""

import argparse

from mcp.server import MCPServer

from agent_lab.synthetic.toolspaces import (
    BASELINE_TOOL_SPACE,
    definitions_for,
    tool_space_names,
)

# The server identity is MCP-visible metadata (it is returned in the initialize result), so it
# is neutral, domain-plausible naming rather than anything that announces a laboratory or an
# evaluation. A model that can tell it is inside experimental apparatus is not observed under
# the conditions we intend to measure. See SPEC.md s6.13 and s9.4.
SERVER_NAME = "customer-directory"
SERVER_VERSION = "1.0.0"


def build_server(tool_space: str = BASELINE_TOOL_SPACE) -> MCPServer:
    """Construct a server exposing exactly the tools in `tool_space`."""
    server: MCPServer = MCPServer(name=SERVER_NAME, version=SERVER_VERSION)
    for definition in definitions_for(tool_space):
        server.tool(name=definition.name, description=definition.description)(definition.fn)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic synthetic MCP environment.")
    parser.add_argument(
        "--tool-space",
        default=BASELINE_TOOL_SPACE,
        choices=tool_space_names(),
        help="Capability surface to expose (default: %(default)s).",
    )
    args = parser.parse_args()
    build_server(args.tool_space).run(transport="stdio")


if __name__ == "__main__":
    main()
