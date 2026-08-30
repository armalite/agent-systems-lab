"""The provider-neutral model adapter interface.

An adapter represents **one model turn**, not a whole agent loop. The runner owns the loop and
executes tools over MCP itself. That split keeps the agent loop legible in one place, keeps
tool execution and tracing in the harness, and prevents provider-specific behaviour from
quietly becoming experimental behaviour.

`render_tools` exists because a provider re-serializes the capability surface into its own tool
format. The runner records the rendered output in the trace, so the surface actually presented
to the model is preserved as evidence rather than assumed to equal the MCP surface.
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from agent_lab.environments.surface import ModelSurface, fingerprint


class ProviderSurface(BaseModel):
    """Stable provider-facing capability and configuration surface.

    Distinct from `ModelSurface`: this is what the *provider* is told, after the adapter has
    re-serialized the canonical surface into the provider's own tool format. The two are not
    semantically identical - the Anthropic tool schema has no output-schema field, for
    instance - which is precisely why they are fingerprinted separately.

    Deliberately excludes messages. Per `SPEC.md` s9.2 (v2.3), a fingerprint over this material
    must never be described as a fingerprint of the exact request.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    system_instructions: str
    tools: tuple[dict[str, Any], ...]
    tool_choice: dict[str, Any] | None = None
    controls: dict[str, Any] = Field(default_factory=dict)

    def canonical_form(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "system_instructions": self.system_instructions,
            "tools": sorted(self.tools, key=lambda tool: str(tool.get("name", ""))),
            "tool_choice": self.tool_choice,
            "controls": self.controls,
        }

    def fingerprint(self) -> str:
        return fingerprint(self.canonical_form())


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    content: Any

    provider_blocks: tuple[dict[str, Any], ...] | None = None
    """Opaque provider-native assistant blocks, preserved verbatim.

    Some providers require assistant content - thinking and redacted-thinking blocks in
    particular - to be echoed back **unchanged** on subsequent tool-use turns. Reconstructing
    them from the neutral view would silently corrupt the continuation.

    The runner never interprets this field; only the adapter that produced it reads it back
    (`SPEC.md` s9.1, v2.3).
    """


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    system_instructions: str
    messages: tuple[Message, ...]
    rendered_tools: tuple[dict[str, Any], ...]
    """Exactly what the adapter presents as the tool surface - preserved in the trace."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    tool_calls: tuple[ToolCallRequest, ...] = ()
    usage: dict[str, Any] | None = None
    latency_ms: float | None = None
    provider_request_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    """Serializable provider metadata. Never normalized away (`SPEC.md` s9.1)."""

    provider_blocks: tuple[dict[str, Any], ...] | None = None
    """Provider-native assistant blocks to replay verbatim on the next turn. See `Message`."""


@runtime_checkable
class ModelAdapter(Protocol):
    """One model turn, provider-neutral.

    Deliberately minimal. An adapter with a distinct provider boundary may additionally expose
    `provider_surface(surface) -> ProviderSurface` and `build_request(request) -> dict`; the
    runner probes for those and records the extra evidence when they exist. Requiring them here
    would force meaningless implementations onto adapters that have no provider boundary.
    """

    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    def render_tools(self, surface: ModelSurface) -> tuple[dict[str, Any], ...]:
        """Serialize the model surface into this provider's tool representation."""
        ...

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Produce exactly one model turn."""
        ...
