"""Controlled procedural memory as an experimental surface (`SPEC.md` s4.3.2, Milestone 5).

Three objects are kept distinct, because a later experiment must be able to tell which one
changed:

- `MemoryDescriptor` - the complete declared material, including hidden provenance;
- `MemoryPolicy`     - the versioned deterministic rule choosing which entries are active;
- `MemorySurface`    - the exact ordered content and placement the model actually sees.

This is not a memory subsystem. There is no store, no retrieval index, no writing, no rewriting,
and no autonomous behaviour of any kind: memory is declared input, resolved once per run by the
runner, and recorded as evidence.
"""

from agent_lab.memory.descriptor import (
    LifecycleState,
    MemoryDescriptor,
    MemoryEntry,
    OriginType,
    load_memory_descriptor,
)
from agent_lab.memory.policy import (
    ACTIVE_DECLARED_ORDER_V1,
    MEMORY_POLICIES,
    MemoryPolicy,
    MemoryPolicyDefinition,
    build_policy,
)
from agent_lab.memory.presentation import (
    LEADING_USER_MEMORY_V1,
    MEMORY_PRESENTATIONS,
    MemoryPresentationDefinition,
    MemorySurface,
    build_presentation,
    render_surface,
)
from agent_lab.memory.resolve import DeclaredMemory, ResolvedMemory, resolve_memory

__all__ = [
    "ACTIVE_DECLARED_ORDER_V1",
    "LEADING_USER_MEMORY_V1",
    "MEMORY_POLICIES",
    "MEMORY_PRESENTATIONS",
    "DeclaredMemory",
    "LifecycleState",
    "MemoryDescriptor",
    "MemoryEntry",
    "MemoryPolicy",
    "MemoryPolicyDefinition",
    "MemoryPresentationDefinition",
    "MemorySurface",
    "OriginType",
    "ResolvedMemory",
    "build_policy",
    "build_presentation",
    "load_memory_descriptor",
    "render_surface",
    "resolve_memory",
]
