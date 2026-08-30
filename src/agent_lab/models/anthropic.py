"""Anthropic provider adapter: exactly one model turn.

The runner owns the agent loop; this module never loops. It translates the harness's neutral
conversation into an Anthropic Messages request, issues one request, and maps the response back
without discarding provider-specific information.

Three things about this boundary are load-bearing:

1. **The transformation is lossy and must be inspectable.** Anthropic tool definitions carry
   `name`, `description`, and `input_schema` only - there is no output-schema field. Our
   canonical `ModelSurface` has output schemas for every tool, so what Claude sees is
   materially narrower than the MCP surface. That is why the two are fingerprinted separately
   rather than assumed equivalent.
2. **Assistant blocks must be replayed verbatim.** Thinking and redacted-thinking blocks have to
   be echoed back unchanged on subsequent tool-use turns, so they are carried opaquely through
   `Message.provider_blocks` rather than reconstructed.
3. **No `temperature`.** It is removed on Claude Opus 5 and rejected with a 400. Variance is
   controlled by repetitions plus explicitly declared thinking/effort controls (`SPEC.md` s18,
   v2.3).
"""

import json
import time
from typing import TYPE_CHECKING, Any, cast

import anthropic

from agent_lab.environments.surface import ModelSurface, canonical_json, fingerprint
from agent_lab.models.base import (
    Message,
    ModelRequest,
    ModelResponse,
    ProviderSurface,
    ToolCallRequest,
)
from agent_lab.models.provider import PaidExecutionGate, ProviderCallError, redact

if TYPE_CHECKING:  # pragma: no cover - typing only
    from anthropic import AsyncAnthropic

PROVIDER = "anthropic"

# Controls the harness declares explicitly rather than inheriting from provider defaults.
DECLARED_CONTROL_KEYS = ("max_tokens", "thinking", "output_config")


class AnthropicAdapter:
    """One Anthropic model turn.

    The client is constructed lazily, only once the paid gate has authorized spending, so
    importing or constructing the adapter never requires credentials.
    """

    def __init__(
        self,
        *,
        model: str,
        parameters: dict[str, Any],
        gate: PaidExecutionGate,
        client: "AsyncAnthropic | None" = None,
    ) -> None:
        if "temperature" in parameters:
            raise ValueError(
                "temperature is not a supported control on current Claude models and is "
                "rejected by the API. Use repetitions plus explicit thinking/effort controls "
                "(SPEC.md s18, v2.3)."
            )
        self._model = model
        self._parameters = dict(parameters)
        self._gate = gate
        self._client = client

    @property
    def provider(self) -> str:
        return PROVIDER

    @property
    def model(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Surface transformation
    # ------------------------------------------------------------------

    def render_tools(self, surface: ModelSurface) -> tuple[dict[str, Any], ...]:
        """Canonical tools -> Anthropic tool definitions.

        `title`, `output_schema`, and `annotations` have no place in the Anthropic tool schema
        and are dropped here. The loss is deliberate, recorded in the provider surface, and
        asserted by test - it is not an oversight.
        """
        return tuple(
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema,
            }
            for tool in sorted(surface.tools, key=lambda tool: tool.name)
        )

    def provider_surface(self, surface: ModelSurface) -> ProviderSurface:
        return ProviderSurface(
            provider=PROVIDER,
            model=self._model,
            system_instructions=surface.system_instructions,
            tools=self.render_tools(surface),
            tool_choice=None,
            controls={
                key: self._parameters[key]
                for key in DECLARED_CONTROL_KEYS
                if key in self._parameters
            },
        )

    # ------------------------------------------------------------------
    # Request construction
    # ------------------------------------------------------------------

    def build_request(self, request: ModelRequest) -> dict[str, Any]:
        """The exact keyword arguments passed to `messages.create`.

        This is the object persisted as evidence for the turn - not a reconstruction of it.
        """
        body: dict[str, Any] = {
            "model": self._model,
            "system": request.system_instructions,
            "tools": list(request.rendered_tools),
            "messages": self._to_anthropic_messages(request.messages),
        }
        body.update(self._parameters)
        return body

    def _to_anthropic_messages(self, messages: tuple[Message, ...]) -> list[dict[str, Any]]:
        """Neutral conversation -> Anthropic messages.

        Consecutive tool observations are merged into a single user message: splitting parallel
        `tool_result` blocks across messages trains the model to stop calling tools in parallel.
        """
        out: list[dict[str, Any]] = []
        pending_results: list[dict[str, Any]] = []

        def flush() -> None:
            if pending_results:
                out.append({"role": "user", "content": list(pending_results)})
                pending_results.clear()

        for message in messages:
            if message.role == "tool":
                pending_results.append(self._tool_result_block(message))
                continue
            flush()
            if message.role == "assistant":
                if message.provider_blocks is None:
                    raise ValueError(
                        "an assistant turn reached the Anthropic adapter without provider "
                        "blocks; continuation content must be replayed verbatim"
                    )
                out.append({"role": "assistant", "content": list(message.provider_blocks)})
            else:
                out.append({"role": message.role, "content": message.content})
        flush()
        return out

    @staticmethod
    def _tool_result_block(message: Message) -> dict[str, Any]:
        content = cast(dict[str, Any], message.content)
        result = content.get("result")
        return {
            "type": "tool_result",
            "tool_use_id": str(content["call_id"]),
            "content": json.dumps(result, ensure_ascii=False, sort_keys=True),
            "is_error": bool(content.get("is_error", False)),
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _build_client(self) -> "AsyncAnthropic":
        # max_retries=0: a silent replay of a failed turn could change the tool-call
        # trajectory, which would make the substantive-call sequence ambiguous.
        return anthropic.AsyncAnthropic(max_retries=0)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self._gate.consume()
        client = self._client if self._client is not None else self._build_client()
        body = self.build_request(request)

        create = cast(Any, client.messages.create)
        started = time.perf_counter()
        try:
            message: Any = await create(**body)
        except anthropic.RateLimitError as exc:
            raise ProviderCallError("rate_limit", str(exc)) from exc
        except anthropic.APIStatusError as exc:
            kind = "server_error" if exc.status_code >= 500 else "api_status_error"
            raise ProviderCallError(kind, f"{exc.status_code}: {exc}") from exc
        except anthropic.APITimeoutError as exc:
            raise ProviderCallError("timeout", str(exc)) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderCallError("connection_error", str(exc)) from exc
        latency_ms = (time.perf_counter() - started) * 1000

        return self._to_model_response(message, latency_ms)

    @staticmethod
    def _to_model_response(message: Any, latency_ms: float) -> ModelResponse:
        """Anthropic response -> neutral response, preserving everything provider-specific."""
        blocks: list[dict[str, Any]] = [
            cast(dict[str, Any], block.model_dump(mode="json")) for block in message.content
        ]

        texts = [str(block["text"]) for block in blocks if block.get("type") == "text"]
        text = "\n".join(texts) if texts else None

        tool_calls = tuple(
            ToolCallRequest(
                call_id=str(block["id"]),
                # Anthropic mints opaque `toolu_...` ids. They are used verbatim: nothing
                # derived from task, condition, run, or execution ever becomes a call id
                # (Observation O-002).
                name=str(block["name"]),
                arguments=cast(dict[str, Any], block.get("input") or {}),
            )
            for block in blocks
            if block.get("type") == "tool_use"
        )

        usage = (
            cast(dict[str, Any], message.usage.model_dump(mode="json"))
            if getattr(message, "usage", None) is not None
            else None
        )
        stop_details = getattr(message, "stop_details", None)

        raw: dict[str, Any] = {
            "stop_reason": getattr(message, "stop_reason", None),
            "stop_details": (
                cast(dict[str, Any], stop_details.model_dump(mode="json"))
                if stop_details is not None
                else None
            ),
            # The alias requested is not necessarily what served the request.
            "served_model": getattr(message, "model", None),
            "message_id": getattr(message, "id", None),
            "content_block_types": [block.get("type") for block in blocks],
        }

        return ModelResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=latency_ms,
            provider_request_id=getattr(message, "_request_id", None),
            raw=raw,
            provider_blocks=tuple(blocks),
        )


def redacted_request(body: dict[str, Any]) -> dict[str, Any]:
    """The exact request body, scrubbed of anything credential-shaped, ready to persist."""
    return cast(dict[str, Any], redact(body))


def exact_request_hash(body: dict[str, Any]) -> str:
    """Hash of the exact full request, computed after redaction.

    Distinct from `provider_surface_fingerprint`: this covers the messages too, so it changes
    every turn. It identifies one request; it is not a comparison aid (`SPEC.md` s9.2, v2.3).
    """
    return fingerprint(json.loads(canonical_json(redacted_request(body))))
