"""The model-visible memory surface and how it is rendered.

`SPEC.md` s4.3.2 (v2.10) fixes M5 to exactly one placement: a **separate leading user-role
message** inserted before the task/conversation messages, replayed unchanged on every model turn
of the run. Memory is never merged into `system_instructions`, because the capability
`model_surface_fingerprint` covers system instructions and must stay independent of per-run
memory.

The wrapper is the only string the harness itself contributes to the model's view of memory, so
it is deliberately minimal and asserts nothing: no provenance, no lifecycle, no condition, no
memory ids, no research framing. Changing the wrapper text, the separator, the ordering, the
role, or the placement is a change to model-visible experimental material and requires a **new
presentation id**, exactly as for metric and policy definitions.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from agent_lab.environments.surface import fingerprint

LEADING_USER_MEMORY_V1 = "leading_user_memory_v1"

_LEADING_USER_MEMORY_V1_SPEC = """\
One user-role message placed before every other message of the conversation, present on every
model turn of the run and byte-identical on each of them.

Rendering: the header line, a blank line, then each active entry's model_visible_content in
selected order, separated by a blank line. Nothing else is added: no memory ids, no origin or
lifecycle labels, no dependency or fingerprint metadata, no condition or experiment identifiers,
no counts, no ordinals.

When the active set is empty, no message is rendered and none is inserted into the request.
"""


@dataclass(frozen=True)
class MemoryPresentationDefinition:
    """A frozen, versioned rendering and placement rule."""

    id: str
    version: str
    role: str
    placement: str
    header: str
    entry_separator: str
    specification: str

    def render(self, contents: Sequence[str]) -> str | None:
        """The exact message text, or None when there is nothing to present."""
        if not contents:
            return None
        return self.header + "\n\n" + self.entry_separator.join(contents)


MEMORY_PRESENTATIONS: dict[str, MemoryPresentationDefinition] = {
    LEADING_USER_MEMORY_V1: MemoryPresentationDefinition(
        id=LEADING_USER_MEMORY_V1,
        version="1.0.0",
        role="user",
        placement="leading_message",
        header="Notes:",
        entry_separator="\n\n",
        specification=_LEADING_USER_MEMORY_V1_SPEC,
    )
}


class MemorySurface(BaseModel):
    """Exactly what the model is shown as memory, and nothing else.

    Hidden provenance is excluded by construction: only content that was actually rendered, the
    order it was rendered in, and the presentation identity/placement appear here. Changing an
    entry's source traces or capability dependencies therefore leaves this fingerprint alone,
    while changing rendered content, order, wrapper, or placement moves it (`SPEC.md` s4.3.2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    presentation_id: str
    presentation_version: str
    role: str
    placement: str
    ordered_content: tuple[str, ...]
    rendered_message: str | None
    """None for the canonical empty surface: resolution happened and produced nothing to show.
    It is evidence that memory resolved to empty, never evidence that the model saw an empty
    wrapper (`SPEC.md` s4.3.2, v2.10)."""

    @property
    def entry_count(self) -> int:
        return len(self.ordered_content)

    @property
    def is_empty(self) -> bool:
        return self.rendered_message is None

    def canonical_form(self) -> dict[str, Any]:
        return {
            "presentation_id": self.presentation_id,
            "presentation_version": self.presentation_version,
            "role": self.role,
            "placement": self.placement,
            "entry_count": self.entry_count,
            "ordered_content": list(self.ordered_content),
            "rendered_message": self.rendered_message,
        }

    def fingerprint(self) -> str:
        return fingerprint(self.canonical_form())


def build_presentation(presentation_id: str) -> MemoryPresentationDefinition:
    definition = MEMORY_PRESENTATIONS.get(presentation_id)
    if definition is None:
        raise ValueError(
            f"unknown memory presentation {presentation_id!r}; "
            f"known: {sorted(MEMORY_PRESENTATIONS)}"
        )
    return definition


def render_surface(
    definition: MemoryPresentationDefinition, contents: Sequence[str]
) -> MemorySurface:
    ordered = tuple(contents)
    return MemorySurface(
        presentation_id=definition.id,
        presentation_version=definition.version,
        role=definition.role,
        placement=definition.placement,
        ordered_content=ordered,
        rendered_message=definition.render(ordered),
    )
