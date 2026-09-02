"""Declared memory, and its once-per-run resolution into a model-visible surface.

The chain `SPEC.md` s4.3.2 requires is explicit here:

    declared descriptor -> versioned policy -> ordered active entries -> rendered surface

`DeclaredMemory` is what an experiment binds at load time - material and policy, both
fingerprinted, neither yet resolved. `resolve_memory` is what the **runner** calls once per run,
before the first model request. Provider adapters never see any of this; they receive an
already-resolved message like any other (acceptance 6).

Resolution is a pure function of the declared corpus and the policy, so it is invariant across
every model turn of a run and identical for every run of an execution. Recomputing it per run
costs nothing and keeps "resolved once at run start" literally true in the code.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from agent_lab.memory.descriptor import MemoryDescriptor
from agent_lab.memory.policy import MemoryPolicy
from agent_lab.memory.presentation import (
    MemoryPresentationDefinition,
    MemorySurface,
    render_surface,
)


class DeclaredMemory(BaseModel):
    """The declared, unresolved memory input of an experiment."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    descriptor: MemoryDescriptor
    policy: MemoryPolicy
    presentation: MemoryPresentationDefinition

    def descriptor_fingerprint(self) -> str:
        return self.descriptor.fingerprint()

    def policy_fingerprint(self) -> str:
        return self.policy.fingerprint()

    def fingerprints(self) -> dict[str, str]:
        """The two identities that bind memory into the resolved experiment configuration."""
        return {
            "memory_descriptor_fingerprint": self.descriptor_fingerprint(),
            "memory_policy_fingerprint": self.policy_fingerprint(),
        }


class ResolvedMemory(BaseModel):
    """One run's resolved memory: what was selected, in what order, rendered how."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    declared: DeclaredMemory
    active_entry_ids: tuple[str, ...]
    surface: MemorySurface

    @property
    def rendered_message(self) -> str | None:
        return self.surface.rendered_message

    def trace_payload(self) -> dict[str, Any]:
        """Evidence for `MEMORY_SURFACE_RESOLVED`.

        Self-contained: the full declared descriptor is included alongside the resolved
        selection, so the selection can be re-checked from the trace alone without consulting
        the experiment definition (`SPEC.md` s18: the raw trace is authoritative).
        """
        return {
            "memory_descriptor": self.declared.descriptor.canonical_form(),
            "memory_descriptor_fingerprint": self.declared.descriptor_fingerprint(),
            "memory_policy": self.declared.policy.canonical_form(),
            "memory_policy_fingerprint": self.declared.policy_fingerprint(),
            "memory_surface": self.surface.canonical_form(),
            "memory_surface_fingerprint": self.surface.fingerprint(),
            "presentation_id": self.surface.presentation_id,
            "presentation_version": self.surface.presentation_version,
            "placement": self.surface.placement,
            "role": self.surface.role,
            "declared_entry_count": len(self.declared.descriptor.entries),
            "memory_entry_count": self.surface.entry_count,
            "active_entry_ids": list(self.active_entry_ids),
            "rendered_message": self.surface.rendered_message,
            "message_inserted": not self.surface.is_empty,
        }

    def result_fields(self) -> dict[str, Any]:
        """The concise normalized fields (`SPEC.md` s4.3.2)."""
        return {
            "memory_descriptor_fingerprint": self.declared.descriptor_fingerprint(),
            "memory_policy_fingerprint": self.declared.policy_fingerprint(),
            "memory_surface_fingerprint": self.surface.fingerprint(),
            "memory_entry_count": self.surface.entry_count,
        }


def resolve_memory(declared: DeclaredMemory) -> ResolvedMemory:
    """Apply the declared policy to the declared corpus and render the surface."""
    active = declared.policy.select(declared.descriptor.entries)
    surface = render_surface(
        declared.presentation, [entry.model_visible_content for entry in active]
    )
    return ResolvedMemory(
        declared=declared,
        active_entry_ids=tuple(entry.memory_id for entry in active),
        surface=surface,
    )
