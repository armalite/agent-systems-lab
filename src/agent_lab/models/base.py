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

from agent_lab.environments.surface import ModelSurface


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    content: Any


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


@runtime_checkable
class ModelAdapter(Protocol):
    """One model turn, provider-neutral."""

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
