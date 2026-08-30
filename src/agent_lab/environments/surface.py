"""Canonical environment and model-surface representations, and their fingerprints.

`SPEC.md` s9.2 requires two distinct objects, and conflating them would be a methodological
error:

- **`EnvironmentDescriptor`** - the semantic MCP/environment state the *harness* observes,
  including server identity, server instructions, declared version, and capability metadata.
- **`ModelSurface`** - the capability surface actually presented to the model adapter.

Metadata visible to the MCP client is not automatically visible to the model. `serverInfo` is
observed by the harness and belongs in the descriptor, but it must not move the model-surface
fingerprint unless the harness actually puts it in the model request - which it does not.

The practical consequence: swapping the server's name changes the environment fingerprint and
leaves the model-surface fingerprint untouched, because nothing the model sees has changed.
"""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict

FINGERPRINT_ALGORITHM = "fp1:sha256"
"""Versioned tag. Bump `fp1` if the canonicalization rules themselves change, so that
fingerprints produced by different rules can never be mistaken for comparable values."""


def canonical_json(value: Any) -> str:
    """Deterministic serialization: sorted keys, no incidental whitespace, UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{FINGERPRINT_ALGORITHM}:{digest}"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CanonicalTool(_Frozen):
    """One tool reduced to its model-relevant semantic content.

    Generated schema metadata (pydantic titles, enum labels) is included deliberately: per
    Observation O-001 it reaches the model, so it is experimental material.
    """

    name: str
    title: str | None
    description: str | None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    annotations: dict[str, Any] | None

    def canonical_form(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "annotations": self.annotations,
        }


class ModelSurface(_Frozen):
    """Exactly what is presented to the model adapter, and nothing else.

    Includes the harness-supplied system instructions, because those are model-visible context
    that forms part of the capability surface under test (`SPEC.md` s9.2).
    """

    system_instructions: str
    tools: tuple[CanonicalTool, ...]

    def canonical_form(self) -> dict[str, Any]:
        return {
            "system_instructions": self.system_instructions,
            "tools": [tool.canonical_form() for tool in sorted(self.tools, key=lambda t: t.name)],
        }

    def fingerprint(self) -> str:
        return fingerprint(self.canonical_form())

    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(tool.name for tool in self.tools))


class ServerIdentity(_Frozen):
    name: str
    title: str | None
    version: str | None
    description: str | None


class EnvironmentDescriptor(_Frozen):
    """Semantic MCP/environment state observed by the harness.

    `observed_context` records details that are real but incidental to meaning - protocol and
    SDK versions. They are persisted so a change is never invisible, but they are excluded from
    the fingerprint so that an SDK upgrade does not masquerade as an environment change.
    """

    environment_id: str
    environment_version: str
    tool_space_id: str
    server: ServerIdentity
    server_instructions: str | None
    capabilities: dict[str, Any]
    tools: tuple[CanonicalTool, ...]
    observed_context: dict[str, Any]

    def canonical_form(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "environment_version": self.environment_version,
            "tool_space_id": self.tool_space_id,
            "server": self.server.model_dump(),
            "server_instructions": self.server_instructions,
            "capabilities": self.capabilities,
            "tools": [tool.canonical_form() for tool in sorted(self.tools, key=lambda t: t.name)],
        }

    def fingerprint(self) -> str:
        return fingerprint(self.canonical_form())

    def model_surface(self, system_instructions: str) -> ModelSurface:
        """Project to what the model will actually receive.

        Server identity, server instructions, capabilities, and observed context are all
        dropped: the harness does not put them in the model request.
        """
        return ModelSurface(system_instructions=system_instructions, tools=self.tools)
