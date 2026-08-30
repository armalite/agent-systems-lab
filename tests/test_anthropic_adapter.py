"""Anthropic adapter behaviour, entirely offline.

Every test here injects a fake client. No network, no credentials, no cost.
"""

import asyncio
import json
from typing import Any

import anthropic
import pytest

from agent_lab.environments.surface import CanonicalTool, ModelSurface
from agent_lab.models.anthropic import AnthropicAdapter, exact_request_hash, redacted_request
from agent_lab.models.base import Message, ModelRequest
from agent_lab.models.provider import PaidExecutionGate, ProviderCallError
from tests.anthropic_doubles import (
    FAKE_REQUEST_ID,
    FakeAnthropicClient,
    build_message,
    text_block,
    thinking_block,
    tool_use_block,
)

SYSTEM = "You are a customer support assistant."


def _surface() -> ModelSurface:
    return ModelSurface(
        system_instructions=SYSTEM,
        tools=(
            CanonicalTool(
                name="get_customer",
                title="Get Customer",
                description="Retrieve a customer record by its customer ID.",
                input_schema={
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}},
                    "required": ["customer_id"],
                },
                output_schema={"type": "object", "properties": {"found": {"type": "boolean"}}},
                annotations={"readOnlyHint": True},
            ),
        ),
    )


def _gate(authorized: bool = True, budget: int | None = 10) -> PaidExecutionGate:
    return PaidExecutionGate(provider="anthropic", authorized=authorized, max_requests=budget)


def _adapter(client: FakeAnthropicClient | None = None, **kwargs: Any) -> AnthropicAdapter:
    return AnthropicAdapter(
        model="claude-opus-5",
        parameters=kwargs.pop(
            "parameters",
            {
                "max_tokens": 4096,
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": "high"},
            },
        ),
        gate=kwargs.pop("gate", _gate()),
        client=client,  # type: ignore[arg-type]
    )


def _request(messages: tuple[Message, ...], adapter: AnthropicAdapter) -> ModelRequest:
    surface = _surface()
    return ModelRequest(
        system_instructions=surface.system_instructions,
        messages=messages,
        rendered_tools=adapter.render_tools(surface),
        parameters={},
        metadata={"task_id": "t", "tool_space_id": "customer_baseline_v1", "step": 0},
    )


# ---------------------------------------------------------------- tool rendering


def test_render_tools_produces_the_anthropic_shape() -> None:
    rendered = _adapter().render_tools(_surface())
    assert len(rendered) == 1
    assert set(rendered[0]) == {"name", "description", "input_schema"}
    assert rendered[0]["name"] == "get_customer"


def test_output_schema_title_and_annotations_are_dropped() -> None:
    """The Anthropic tool schema has no field for these; the loss is deliberate and asserted."""
    rendered = _adapter().render_tools(_surface())[0]
    assert "output_schema" not in rendered
    assert "title" not in rendered
    assert "annotations" not in rendered
    # ...and the canonical surface still carries them.
    assert _surface().tools[0].output_schema is not None


def test_provider_surface_differs_from_model_surface() -> None:
    """Two boundaries, two fingerprints. Treating them as equal would be a methodological error."""
    surface = _surface()
    provider_surface = _adapter().provider_surface(surface)
    assert provider_surface.fingerprint() != surface.fingerprint()
    assert provider_surface.controls["thinking"] == {"type": "adaptive"}
    assert provider_surface.controls["output_config"] == {"effort": "high"}


def test_provider_surface_excludes_messages() -> None:
    """It is a comparison aid, not a request hash (`SPEC.md` s9.2, v2.3)."""
    assert "messages" not in _adapter().provider_surface(_surface()).canonical_form()


def test_provider_surface_fingerprint_tracks_declared_controls() -> None:
    surface = _surface()
    high = _adapter().provider_surface(surface).fingerprint()
    low = (
        _adapter(
            parameters={
                "max_tokens": 4096,
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": "low"},
            }
        )
        .provider_surface(surface)
        .fingerprint()
    )
    assert high != low


# ---------------------------------------------------------------- request building


def test_temperature_is_rejected_at_construction() -> None:
    """Unsupported on current Claude models; the API returns 400 (`SPEC.md` s18, v2.3)."""
    with pytest.raises(ValueError, match="temperature is not a supported control"):
        AnthropicAdapter(
            model="claude-opus-5",
            parameters={"max_tokens": 10, "temperature": 0},
            gate=_gate(),
        )


def test_request_body_carries_declared_controls() -> None:
    adapter = _adapter()
    body = adapter.build_request(_request((Message(role="user", content="hi"),), adapter))
    assert body["model"] == "claude-opus-5"
    assert body["system"] == SYSTEM
    assert body["max_tokens"] == 4096
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "high"}
    assert "temperature" not in body


def test_consecutive_tool_results_merge_into_one_user_message() -> None:
    """Splitting parallel tool results trains the model to stop calling tools in parallel."""
    adapter = _adapter()
    messages = (
        Message(role="user", content="hi"),
        Message(role="assistant", content={}, provider_blocks=({"type": "text", "text": "x"},)),
        Message(
            role="tool",
            content={"call_id": "a", "name": "t", "result": {"ok": 1}, "is_error": False},
        ),
        Message(
            role="tool",
            content={"call_id": "b", "name": "t", "result": {"ok": 2}, "is_error": False},
        ),
    )
    body = adapter.build_request(_request(messages, adapter))
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert len(body["messages"][2]["content"]) == 2
    assert body["messages"][2]["content"][0]["tool_use_id"] == "a"


def test_tool_errors_are_marked_is_error() -> None:
    adapter = _adapter()
    messages = (
        Message(role="user", content="hi"),
        Message(role="assistant", content={}, provider_blocks=({"type": "text", "text": "x"},)),
        Message(
            role="tool",
            content={
                "call_id": "a",
                "name": "t",
                "result": {"error": "unknown_tool"},
                "is_error": True,
            },
        ),
    )
    body = adapter.build_request(_request(messages, adapter))
    assert body["messages"][2]["content"][0]["is_error"] is True


def test_assistant_turn_without_provider_blocks_is_refused() -> None:
    """Reconstructing continuation blocks would silently corrupt the turn."""
    adapter = _adapter()
    messages = (
        Message(role="user", content="hi"),
        Message(role="assistant", content={"text": "x"}),
    )
    with pytest.raises(ValueError, match="provider blocks"):
        adapter.build_request(_request(messages, adapter))


# ---------------------------------------------------------------- response mapping


def test_text_response_maps_cleanly() -> None:
    client = FakeAnthropicClient([build_message(blocks=[text_block("The email is x@y.test.")])])
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert response.text == "The email is x@y.test."
    assert response.tool_calls == ()
    assert response.provider_request_id == FAKE_REQUEST_ID
    assert response.raw["stop_reason"] == "end_turn"
    assert response.raw["served_model"] == "claude-opus-5-served"
    assert response.usage is not None and response.usage["input_tokens"] == 1234
    assert response.latency_ms is not None


def test_tool_use_response_maps_call_ids_verbatim() -> None:
    client = FakeAnthropicClient(
        [
            build_message(
                blocks=[tool_use_block("toolu_abc", "get_customer", {"customer_id": "C102"})],
                stop_reason="tool_use",
            )
        ]
    )
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.call_id == "toolu_abc"
    assert call.arguments == {"customer_id": "C102"}
    assert response.text is None


def test_thinking_blocks_are_preserved_for_verbatim_replay() -> None:
    """Thinking blocks must round-trip unchanged across tool-use turns."""
    client = FakeAnthropicClient(
        [
            build_message(
                blocks=[
                    thinking_block("deliberating"),
                    tool_use_block("toolu_1", "get_customer", {"customer_id": "C102"}),
                ],
                stop_reason="tool_use",
            )
        ]
    )
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert response.provider_blocks is not None
    kinds = [block["type"] for block in response.provider_blocks]
    assert kinds == ["thinking", "tool_use"]
    # Thinking text is never mistaken for the answer.
    assert response.text is None

    replayed = adapter.build_request(
        _request(
            (
                Message(role="user", content="q"),
                Message(role="assistant", content={}, provider_blocks=response.provider_blocks),
            ),
            adapter,
        )
    )
    assert replayed["messages"][1]["content"] == list(response.provider_blocks)


def test_text_preamble_alongside_a_tool_call_is_captured_but_is_not_the_answer() -> None:
    """Observed live: Claude often emits a short text preamble *with* the tool_use block.

    The preamble must be preserved (it is model output) and replayed verbatim, but it must never
    become the task's final answer - only a turn with no tool calls ends the run. Two of three
    live smoke tasks took this shape, and the offline doubles had not covered it.
    """
    client = FakeAnthropicClient(
        [
            build_message(
                blocks=[
                    text_block("I'll look that up for you."),
                    tool_use_block("toolu_x", "get_customer", {"customer_id": "C102"}),
                ],
                stop_reason="tool_use",
            )
        ]
    )
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert response.text == "I'll look that up for you."
    assert len(response.tool_calls) == 1
    assert response.provider_blocks is not None
    assert [block["type"] for block in response.provider_blocks] == ["text", "tool_use"]
    assert response.raw["stop_reason"] == "tool_use"


def test_multiple_text_blocks_are_joined_not_dropped() -> None:
    client = FakeAnthropicClient(
        [build_message(blocks=[text_block("first"), text_block("second")])]
    )
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert response.text == "first\nsecond"


@pytest.mark.parametrize("stop_reason", ["end_turn", "max_tokens", "tool_use", "refusal"])
def test_stop_reason_is_preserved(stop_reason: str) -> None:
    client = FakeAnthropicClient([build_message(blocks=[text_block("x")], stop_reason=stop_reason)])
    adapter = _adapter(client)
    response = asyncio.run(
        adapter.generate(_request((Message(role="user", content="q"),), adapter))
    )
    assert response.raw["stop_reason"] == stop_reason


# ---------------------------------------------------------------- error handling


@pytest.mark.parametrize(
    ("exc", "expected_kind"),
    [
        (anthropic.APIConnectionError(request=None), "connection_error"),  # type: ignore[arg-type]
        (anthropic.APITimeoutError(request=None), "timeout"),  # type: ignore[arg-type]
    ],
)
def test_connection_failures_become_provider_call_errors(
    exc: Exception, expected_kind: str
) -> None:
    adapter = _adapter(FakeAnthropicClient([exc]))
    with pytest.raises(ProviderCallError) as info:
        asyncio.run(adapter.generate(_request((Message(role="user", content="q"),), adapter)))
    assert info.value.kind == expected_kind


def test_the_adapter_never_loops() -> None:
    """One turn per generate() call. The runner owns the agent loop."""
    client = FakeAnthropicClient(
        [
            build_message(
                blocks=[tool_use_block("toolu_1", "get_customer", {"customer_id": "C102"})],
                stop_reason="tool_use",
            )
        ]
    )
    adapter = _adapter(client)
    asyncio.run(adapter.generate(_request((Message(role="user", content="q"),), adapter)))
    assert len(client.requests) == 1


# ---------------------------------------------------------------- redaction


def test_redaction_scrubs_credential_shaped_strings() -> None:
    body = {"system": "key sk-ant-api03-SECRETVALUE123 here", "nested": [{"k": "sk-ant-xyz789"}]}
    scrubbed = redacted_request(body)
    blob = json.dumps(scrubbed)
    assert "SECRETVALUE123" not in blob
    assert "sk-ant-" not in blob
    assert "[REDACTED]" in blob


def test_exact_request_hash_is_deterministic_and_covers_messages() -> None:
    adapter = _adapter()
    one = adapter.build_request(_request((Message(role="user", content="a"),), adapter))
    two = adapter.build_request(_request((Message(role="user", content="b"),), adapter))
    assert exact_request_hash(one) == exact_request_hash(one)
    assert exact_request_hash(one) != exact_request_hash(two)
