"""Deterministic scripted model adapter.

This is a calibration weight, not a model. It replays an explicit script so the harness can be
proven correct while the ground truth is still known - the only window in which harness bugs
are cheap to find.

Two rules keep it honest:

1. **No implicit access to ground truth.** The adapter never reads the task's expected tool or
   answer. An unscripted task raises rather than silently "knowing" what to do.
2. **No randomness and no heuristics.** Identical inputs always replay identical turns.

Scripts are keyed by `(task_id, tool_space_id)`, with `"*"` matching any tool-space. That lets a
test script a difference between conditions in order to exercise comparison logic - which is
fixture data for testing the instrument, never a prediction about model behaviour.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from agent_lab.environments.surface import ModelSurface, fingerprint
from agent_lab.models.base import Message, ModelRequest, ModelResponse, ToolCallRequest

ANY_TOOL_SPACE = "*"


class ScriptedToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ScriptedTurn(BaseModel):
    """One model turn: either tool calls, or a final text answer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_calls: tuple[ScriptedToolCall, ...] = ()
    text: str | None = None


class Script(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    scenario: str
    """Label for readability only. Metrics never read it - outcomes are derived from the trace."""

    tool_space: str = ANY_TOOL_SPACE
    turns: tuple[ScriptedTurn, ...]


class ScriptSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    scripts: tuple[Script, ...]

    def fingerprint(self) -> str:
        return fingerprint(
            {
                "id": self.id,
                "version": self.version,
                "scripts": [
                    script.model_dump(mode="json")
                    for script in sorted(self.scripts, key=lambda s: (s.task_id, s.tool_space))
                ],
            }
        )

    def resolve(self, task_id: str, tool_space_id: str) -> Script:
        """Exact `(task, tool-space)` match wins; otherwise the wildcard entry."""
        exact = [s for s in self.scripts if s.task_id == task_id and s.tool_space == tool_space_id]
        if exact:
            return exact[0]
        wildcard = [
            s for s in self.scripts if s.task_id == task_id and s.tool_space == ANY_TOOL_SPACE
        ]
        if wildcard:
            return wildcard[0]
        raise KeyError(
            f"no script for task {task_id!r} in tool-space {tool_space_id!r}. The scripted "
            "adapter never infers behaviour from expected outcomes; add an explicit script."
        )


def load_script_set(path: Path) -> ScriptSet:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: script set must be a YAML mapping")
    return ScriptSet.model_validate(raw)


class ScriptedAdapter:
    """Replays a script. Turn index comes from the conversation, so replays are stateless."""

    def __init__(self, script_set: ScriptSet, model_name: str = "scripted-v1") -> None:
        self._script_set = script_set
        self._model = model_name

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return self._model

    def render_tools(self, surface: ModelSurface) -> tuple[dict[str, Any], ...]:
        """Identity rendering: the fake presents the canonical surface unchanged.

        A real provider adapter (Milestone 3) will transform this, which is exactly why the
        rendered form is recorded in the trace rather than assumed.
        """
        return tuple(tool.canonical_form() for tool in sorted(surface.tools, key=lambda t: t.name))

    async def generate(self, request: ModelRequest) -> ModelResponse:
        task_id = str(request.metadata["task_id"])
        tool_space_id = str(request.metadata["tool_space_id"])
        script = self._script_set.resolve(task_id, tool_space_id)
        turn_index = _completed_turns(request.messages)

        if turn_index >= len(script.turns):
            # Script exhausted without a final answer: a deterministic "gave up" outcome.
            return ModelResponse(
                text=None,
                tool_calls=(),
                raw={"scenario": script.scenario, "reason": "script_exhausted"},
            )

        turn = script.turns[turn_index]
        return ModelResponse(
            text=turn.text,
            # Call ids are echoed back to the model in the conversation, so they must stay
            # opaque: embedding the task or condition label here would leak the experimental
            # design into model-visible context (Observation O-001).
            tool_calls=tuple(
                ToolCallRequest(
                    call_id=f"call_{turn_index}_{index}",
                    name=call.name,
                    arguments=dict(call.arguments),
                )
                for index, call in enumerate(turn.tool_calls)
            ),
            usage=None,
            # Not part of the conversation; recorded as provider metadata only.
            provider_request_id=f"scripted-{task_id}-{tool_space_id}-{turn_index}",
            raw={"scenario": script.scenario, "turn_index": turn_index},
        )


def _completed_turns(messages: tuple[Message, ...]) -> int:
    """How many model turns have already happened, inferred from the conversation."""
    return sum(1 for message in messages if message.role == "assistant")
