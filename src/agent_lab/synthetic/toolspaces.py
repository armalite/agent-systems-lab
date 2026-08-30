"""Declarative definition of the model-visible capability surface for each condition.

A tool-space is the manipulated variable of the Phase 0 calibration, so the names,
descriptions, and argument shapes exposed to a model are treated as controlled experimental
material and are defined in exactly one place.

Descriptions are written in the neutral register a competent API author would use, and were
fixed before any model experiment was run. `overlap_note` records the *intended* overlap
required by `SPEC.md` s10; it is internal experimental metadata and is deliberately **never
exposed over MCP**, so the model cannot see how the environment was designed.

Per Milestone 1 scope these live as typed Python. Declarative YAML tool-space loading arrives
with the loader in Milestone 2.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent_lab.synthetic import tools

BASELINE_TOOL_SPACE = "customer_baseline_v1"
OVERLAP_TOOL_SPACE = "customer_overlap_v1"


@dataclass(frozen=True)
class ToolDefinition:
    """One tool as the model will see it, plus internal experimental metadata."""

    name: str
    description: str
    fn: Callable[..., Any]
    overlap_note: str | None = None
    """Intended semantic overlap with a baseline tool. Internal only; never sent over MCP."""


_BASELINE: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="get_customer",
        description="Retrieve a customer record by its customer ID.",
        fn=tools.get_customer,
    ),
    ToolDefinition(
        name="get_order",
        description="Retrieve an order record by its order ID.",
        fn=tools.get_order,
    ),
    ToolDefinition(
        name="get_invoice",
        description="Retrieve an invoice record by its invoice ID.",
        fn=tools.get_invoice,
    ),
    ToolDefinition(
        name="get_product",
        description="Retrieve a product record by its product ID.",
        fn=tools.get_product,
    ),
    ToolDefinition(
        name="get_employee",
        description="Retrieve an employee record by its employee ID.",
        fn=tools.get_employee,
    ),
)

_OVERLAP_ONLY: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="find_customer",
        description="Find a customer by their full name.",
        fn=tools.find_customer,
        overlap_note=(
            "Overlaps get_customer on intent (retrieve one customer) but keys on name rather "
            "than customer ID."
        ),
    ),
    ToolDefinition(
        name="search_customers",
        description="Search customers by a free-text query matching name, email, or city.",
        fn=tools.search_customers,
        overlap_note=(
            "Overlaps get_customer on intent but returns zero or more customers rather than one, "
            "and accepts an unstructured query."
        ),
    ),
    ToolDefinition(
        name="get_customer_details",
        description=(
            "Retrieve extended details for a customer by customer ID, including account "
            "management fields."
        ),
        fn=tools.get_customer_details,
        overlap_note=(
            "Accepts the same argument as get_customer and returns a superset of its fields; "
            "the core customer data is identical."
        ),
    ),
    ToolDefinition(
        name="lookup_customer",
        description="Look up a customer by their email address.",
        fn=tools.lookup_customer,
        overlap_note=("Overlaps get_customer on intent but keys on email rather than customer ID."),
    ),
    ToolDefinition(
        name="customer_information",
        description="Get information about a customer by customer ID.",
        fn=tools.customer_information,
        overlap_note=(
            "A near-pure alias of get_customer: same argument, same returned data, differing "
            "only in name and phrasing."
        ),
    ),
)

TOOL_DEFINITIONS: dict[str, ToolDefinition] = {
    definition.name: definition for definition in (*_BASELINE, *_OVERLAP_ONLY)
}

TOOL_SPACES: dict[str, tuple[str, ...]] = {
    BASELINE_TOOL_SPACE: tuple(d.name for d in _BASELINE),
    # Mirrors the `extends: customer_baseline_v1` form in SPEC.md s9.4: the baseline surface
    # is unchanged and the overlapping tools are added to it.
    OVERLAP_TOOL_SPACE: tuple(d.name for d in (*_BASELINE, *_OVERLAP_ONLY)),
}


def tool_space_names() -> tuple[str, ...]:
    return tuple(sorted(TOOL_SPACES))


def definitions_for(tool_space: str) -> tuple[ToolDefinition, ...]:
    """Return the tool definitions exposed by a named tool-space, in registration order."""
    if tool_space not in TOOL_SPACES:
        raise KeyError(
            f"unknown tool-space {tool_space!r}; known tool-spaces: {tool_space_names()}"
        )
    return tuple(TOOL_DEFINITIONS[name] for name in TOOL_SPACES[tool_space])
