"""The declared memory corpus, and its canonical descriptor.

`MemoryDescriptor` is the **complete declared experimental input** (`SPEC.md` s4.3.2, v2.10):
every model-visible string together with every hidden provenance, dependency, and lifecycle
field. Its fingerprint therefore moves when any declared field changes, even when the rendered
model-visible surface is byte-identical - that is the point, because "the same text under
different provenance" is a different experimental input.

Nothing here is model-visible except `model_visible_content`. Origin labels, lifecycle state,
source trace ids, capability dependencies and learned-under fingerprints are harness evidence
and must never reach a provider request (`SPEC.md` s4.3.2: hidden provenance is not prompt
content).
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from agent_lab.environments.surface import fingerprint

OriginType = Literal["trace_derived", "synthetic_control", "hand_authored_control", "transformed"]
"""How the material actually came to exist (`SPEC.md` s4.3.1).

Controlled material must never be presentable as naturally acquired experience, so the
distinction is declared per entry rather than assumed for a corpus.
"""

LifecycleState = Literal["active", "inactive"]
"""Whether an entry is currently eligible for presentation.

Deliberately two neutral values. Reason-carrying labels (`stale`, `invalid`, `revalidate`, and
anything naming a condition) are exactly what `SPEC.md` s4.3.2 forbids leaking, and inventing
them here would also pre-commit the apparatus to one study's lifecycle semantics. Why an entry
is inactive belongs in its provenance fields, not in the state name.
"""

TRACE_BACKED_ORIGINS = frozenset({"trace_derived", "transformed"})
CONTROL_ORIGINS = frozenset({"synthetic_control", "hand_authored_control"})


class MemoryEntry(BaseModel):
    """One controlled memory entry (`SPEC.md` s4.3.2 minimum representation)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_id: str
    model_visible_content: str
    """The only field that ever reaches the model."""

    origin_type: OriginType
    lifecycle_state: LifecycleState

    source_trace_ids: tuple[str, ...] = ()
    derivation_identity: str | None = None
    learned_under_environment_fingerprint: str | None = None
    learned_under_model_surface_fingerprint: str | None = None
    capability_dependencies: tuple[str, ...] = ()

    def model_post_init(self, _context: Any) -> None:
        if not self.model_visible_content.strip():
            raise ValueError(f"memory entry {self.memory_id}: model_visible_content is empty")
        if self.origin_type == "trace_derived" and not self.source_trace_ids:
            raise ValueError(
                f"memory entry {self.memory_id}: trace_derived material must name the source "
                "traces it was derived from, or its derivation is not reproducible "
                "(SPEC.md s4.3.1)"
            )
        if self.origin_type in TRACE_BACKED_ORIGINS and not self.derivation_identity:
            raise ValueError(
                f"memory entry {self.memory_id}: origin {self.origin_type!r} requires a "
                "derivation_identity so the transformation is reproducible (SPEC.md s4.3.1)"
            )
        if self.origin_type in CONTROL_ORIGINS and self.source_trace_ids:
            raise ValueError(
                f"memory entry {self.memory_id}: origin {self.origin_type!r} is controlled "
                "material and must not claim source traces; declare it as trace_derived or "
                "transformed instead (SPEC.md s4.3.1)"
            )

    def canonical_form(self) -> dict[str, Any]:
        """Every declared field, model-visible and hidden alike."""
        return self.model_dump(mode="json")


class MemoryDescriptor(BaseModel):
    """A complete declared memory corpus, in its declared order.

    Order is preserved rather than sorted: declared order determines presentation order, so a
    reordering is a real change to the experimental input and must move the fingerprint.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    entries: tuple[MemoryEntry, ...] = ()
    """May be empty. A declared-but-empty corpus is a legitimate experimental state, distinct
    from declaring no memory at all (`SPEC.md` s4.3.2, v2.10)."""

    def model_post_init(self, _context: Any) -> None:
        ids = [entry.memory_id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError(f"memory corpus {self.id} contains duplicate memory ids")

    def canonical_form(self) -> dict[str, Any]:
        return {
            "memory_set_id": self.id,
            "memory_set_version": self.version,
            "entries": [entry.canonical_form() for entry in self.entries],
        }

    def fingerprint(self) -> str:
        """Content-derived, so the same declared bytes fingerprint identically from any path."""
        return fingerprint(self.canonical_form())


class _MemoryDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    entries: tuple[MemoryEntry, ...] = Field(default_factory=tuple)


def load_memory_descriptor(path: Path) -> MemoryDescriptor:
    """Load declared memory material from YAML.

    The path may live outside the apparatus repository - an experiment in a research workspace
    references its own material - and never enters the fingerprint (`SPEC.md` s4.3.2).
    """
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: memory material must be a YAML mapping")
    document = _MemoryDocument.model_validate(raw)
    return MemoryDescriptor(id=document.id, version=document.version, entries=document.entries)
