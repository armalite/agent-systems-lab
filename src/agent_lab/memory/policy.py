"""Versioned memory-selection policies.

A policy decides which declared entries are active. `SPEC.md` s4.3.2 (v2.10) fixes the identity
semantics: `memory_policy_fingerprint` identifies the **versioned policy definition plus its
canonical parameters**, never the selection outcome. A policy that happens to select nothing on
one corpus has the same fingerprint as the same policy selecting everything on another; which
entries were actually selected is raw trace evidence.

This follows the metric-definition discipline in `agent_lab.evals.metrics`: to change what a
policy means, add a new id. Never edit one in place - that would silently reinterpret evidence
already on disk.

M5 deliberately ships exactly one policy. Ranking, recency, similarity, and turn-varying
retrieval are separate experimental variables, not ergonomic gaps (`SPEC.md` s4.3.2).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agent_lab.environments.surface import fingerprint
from agent_lab.memory.descriptor import MemoryEntry

ACTIVE_DECLARED_ORDER_V1 = "active_declared_order_v1"

_ACTIVE_DECLARED_ORDER_V1_SPEC = """\
Select every declared entry whose lifecycle_state is "active", preserving declared corpus order.

Deterministic and total: no ranking, no scoring, no truncation, no similarity, no dependence on
the task, the tool-space, the model, the turn, or anything observed during the run. The selected
set is therefore a pure function of the declared corpus, and is invariant across every model
turn of the run that resolved it.

Entries whose lifecycle_state is "inactive" are excluded. Selecting zero entries is a valid
outcome and yields a canonical empty memory surface, not an absence of memory configuration.
"""


def _select_active_declared_order(
    entries: Sequence[MemoryEntry], _parameters: Mapping[str, Any]
) -> tuple[MemoryEntry, ...]:
    return tuple(entry for entry in entries if entry.lifecycle_state == "active")


@dataclass(frozen=True)
class MemoryPolicyDefinition:
    """One frozen, named, versioned selection rule."""

    id: str
    version: str
    specification: str
    parameter_names: tuple[str, ...]
    select: Callable[[Sequence[MemoryEntry], Mapping[str, Any]], tuple[MemoryEntry, ...]]

    def canonical_form(self) -> dict[str, Any]:
        """Identity of the definition itself. The callable is behaviour, not identity; the
        specification text is what pins the semantics, exactly as for metric definitions."""
        return {
            "policy_id": self.id,
            "policy_version": self.version,
            "parameter_names": list(self.parameter_names),
            "specification": self.specification,
        }


MEMORY_POLICIES: dict[str, MemoryPolicyDefinition] = {
    ACTIVE_DECLARED_ORDER_V1: MemoryPolicyDefinition(
        id=ACTIVE_DECLARED_ORDER_V1,
        version="1.0.0",
        specification=_ACTIVE_DECLARED_ORDER_V1_SPEC,
        parameter_names=(),
        select=_select_active_declared_order,
    )
}


@dataclass(frozen=True)
class MemoryPolicy:
    """A policy definition bound to the parameters an experiment declared for it."""

    definition: MemoryPolicyDefinition
    parameters: Mapping[str, Any]

    @property
    def id(self) -> str:
        return self.definition.id

    def canonical_form(self) -> dict[str, Any]:
        return {
            "definition": self.definition.canonical_form(),
            "parameters": dict(self.parameters),
        }

    def fingerprint(self) -> str:
        return fingerprint(self.canonical_form())

    def select(self, entries: Sequence[MemoryEntry]) -> tuple[MemoryEntry, ...]:
        return self.definition.select(entries, self.parameters)


def build_policy(policy_id: str, parameters: Mapping[str, Any] | None = None) -> MemoryPolicy:
    """Resolve a declared policy id, rejecting unknown ids and unknown parameters."""
    definition = MEMORY_POLICIES.get(policy_id)
    if definition is None:
        raise ValueError(f"unknown memory policy {policy_id!r}; known: {sorted(MEMORY_POLICIES)}")
    declared = dict(parameters or {})
    unknown = sorted(set(declared) - set(definition.parameter_names))
    if unknown:
        raise ValueError(
            f"memory policy {policy_id!r} accepts no parameter(s) {unknown}; "
            f"declared parameters: {list(definition.parameter_names)}"
        )
    return MemoryPolicy(definition=definition, parameters=declared)
