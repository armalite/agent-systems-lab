"""Regenerate the committed tool-surface snapshots.

Run deliberately, and review the resulting diff: it represents a change to the model-visible
capability surface, which is controlled experimental material.

    uv run python -m tests.regenerate_snapshots
"""

import asyncio
import json
from pathlib import Path

from agent_lab.mcp.client import canonical_tool_surface, synthetic_stdio_client
from agent_lab.synthetic.toolspaces import TOOL_SPACES

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


async def _surface(tool_space: str) -> list[dict[str, object]]:
    async with synthetic_stdio_client(tool_space) as client:
        return canonical_tool_surface((await client.list_tools()).tools)


def main() -> None:
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    for tool_space in TOOL_SPACES:
        surface = asyncio.run(_surface(tool_space))
        path = SNAPSHOT_DIR / f"tool_surface_{tool_space}.json"
        path.write_text(json.dumps(surface, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"wrote {path} ({len(surface)} tools)")


if __name__ == "__main__":
    main()
