"""Offline doubles for the Anthropic client.

Responses are built from the **SDK's own model types**, so the adapter's mapping is tested
against the real response shapes rather than hand-rolled dicts. Nothing here touches the
network, and no client is ever constructed against real credentials.
"""

from typing import Any

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

FAKE_REQUEST_ID = "req_offline_double"


def build_message(
    *,
    blocks: list[Any],
    stop_reason: str = "end_turn",
    model: str = "claude-opus-5-served",
    message_id: str = "msg_offline",
    usage: Usage | None = None,
) -> Message:
    message = Message.model_construct(
        id=message_id,
        content=blocks,
        model=model,
        role="assistant",
        stop_reason=stop_reason,
        stop_sequence=None,
        type="message",
        usage=usage
        or Usage.model_construct(
            input_tokens=1234,
            output_tokens=56,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        ),
    )
    object.__setattr__(message, "_request_id", FAKE_REQUEST_ID)
    return message


def text_block(text: str) -> TextBlock:
    return TextBlock.model_construct(type="text", text=text, citations=None)


def tool_use_block(call_id: str, name: str, arguments: dict[str, Any]) -> ToolUseBlock:
    return ToolUseBlock.model_construct(type="tool_use", id=call_id, name=name, input=arguments)


def thinking_block(text: str, signature: str = "sig-abc") -> Any:
    """A thinking block, which must be replayed verbatim on the next turn."""

    class _Thinking:
        type = "thinking"

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {"type": "thinking", "thinking": text, "signature": signature}

    return _Thinking()


class FakeMessages:
    def __init__(self, responses: list[Message | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("fake client ran out of scripted responses")
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


class FakeAnthropicClient:
    """Stands in for `AsyncAnthropic`. Records every request body it is handed."""

    def __init__(self, responses: list[Message | Exception]) -> None:
        self.messages = FakeMessages(responses)

    @property
    def requests(self) -> list[dict[str, Any]]:
        return self.messages.calls
