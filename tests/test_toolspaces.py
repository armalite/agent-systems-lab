"""Tool-space membership: the declared capability surface per experimental condition."""

import pytest

from agent_lab.synthetic.toolspaces import (
    BASELINE_TOOL_SPACE,
    OVERLAP_TOOL_SPACE,
    TOOL_DEFINITIONS,
    TOOL_SPACES,
    definitions_for,
    tool_space_names,
)

BASELINE_EXPECTED = (
    "get_customer",
    "get_order",
    "get_invoice",
    "get_product",
    "get_employee",
)
OVERLAP_ONLY_EXPECTED = (
    "find_customer",
    "search_customers",
    "get_customer_details",
    "lookup_customer",
    "customer_information",
)


def test_known_tool_spaces() -> None:
    assert tool_space_names() == (BASELINE_TOOL_SPACE, OVERLAP_TOOL_SPACE)


def test_baseline_holds_exactly_the_five_baseline_tools() -> None:
    assert TOOL_SPACES[BASELINE_TOOL_SPACE] == BASELINE_EXPECTED


def test_overlap_extends_baseline_without_altering_it() -> None:
    """SPEC.md s9.4: the overlap condition adds tools; it must not change the baseline five."""
    overlap = TOOL_SPACES[OVERLAP_TOOL_SPACE]
    assert overlap[: len(BASELINE_EXPECTED)] == BASELINE_EXPECTED
    assert overlap[len(BASELINE_EXPECTED) :] == OVERLAP_ONLY_EXPECTED
    assert len(overlap) == 10


def test_tool_space_difference_is_the_manipulated_variable() -> None:
    added = set(TOOL_SPACES[OVERLAP_TOOL_SPACE]) - set(TOOL_SPACES[BASELINE_TOOL_SPACE])
    assert added == set(OVERLAP_ONLY_EXPECTED)


def test_every_definition_has_a_nonempty_description() -> None:
    for definition in TOOL_DEFINITIONS.values():
        assert definition.description.strip()


def test_only_overlap_tools_carry_an_overlap_note() -> None:
    """The documented intent required by SPEC.md s10, kept internal to the harness."""
    for name in BASELINE_EXPECTED:
        assert TOOL_DEFINITIONS[name].overlap_note is None
    for name in OVERLAP_ONLY_EXPECTED:
        note = TOOL_DEFINITIONS[name].overlap_note
        assert note is not None and note.strip()


def test_unknown_tool_space_is_rejected() -> None:
    with pytest.raises(KeyError):
        definitions_for("customer_nonexistent_v9")


def test_definitions_for_returns_registration_order() -> None:
    assert tuple(d.name for d in definitions_for(OVERLAP_TOOL_SPACE)) == (
        *BASELINE_EXPECTED,
        *OVERLAP_ONLY_EXPECTED,
    )
