"""Direct verification of every synthetic tool without any MCP transport.

This is one half of the Milestone 1 acceptance: the underlying behaviour must be deterministic
and testable on its own, so that later failures can be attributed to the model or the transport
rather than to the environment.
"""

import ast
from importlib.resources import files

import pytest

from agent_lab.synthetic import tools
from agent_lab.synthetic.toolspaces import TOOL_DEFINITIONS
from tests.calls import MISSING_CALLS, VALID_CALLS


def test_every_defined_tool_is_covered_by_a_direct_call() -> None:
    assert set(VALID_CALLS) == set(TOOL_DEFINITIONS)


@pytest.mark.parametrize("tool_name", sorted(VALID_CALLS))
def test_every_tool_returns_fixture_data_without_mcp(tool_name: str) -> None:
    result = TOOL_DEFINITIONS[tool_name].fn(**VALID_CALLS[tool_name])
    payload = result.model_dump()
    if "found" in payload:
        assert payload["found"] is True
    else:
        assert payload["match_count"] >= 1


@pytest.mark.parametrize("tool_name", sorted(VALID_CALLS))
def test_repeated_identical_calls_are_byte_identical(tool_name: str) -> None:
    """Determinism is the property the whole instrument rests on."""
    call = VALID_CALLS[tool_name]
    fn = TOOL_DEFINITIONS[tool_name].fn
    first = fn(**call).model_dump_json()
    for _ in range(5):
        assert fn(**call).model_dump_json() == first


@pytest.mark.parametrize("tool_name", sorted(MISSING_CALLS))
def test_misses_return_structured_not_found_rather_than_raising(tool_name: str) -> None:
    """A miss must stay distinguishable from a transport failure."""
    result = TOOL_DEFINITIONS[tool_name].fn(**MISSING_CALLS[tool_name])
    payload = result.model_dump()
    assert payload["found"] is False
    assert payload["message"]


def test_specific_baseline_answers() -> None:
    customer = tools.get_customer("C102").customer
    assert customer is not None
    assert customer.email == "priya.r@example.test"

    order = tools.get_order("O204").order
    assert order is not None
    assert order.status == "pending"

    invoice = tools.get_invoice("I304").invoice
    assert invoice is not None
    assert invoice.amount_due == 391.10

    product = tools.get_product("P502").product
    assert product is not None
    assert product.category == "stationery"

    employee = tools.get_employee("E104").employee
    assert employee is not None
    assert employee.office == "Porto Alegre"


def test_overlapping_tools_agree_with_the_baseline_tool() -> None:
    """The core consistency guarantee: a wrong tool choice never yields contradictory data."""
    baseline = tools.get_customer("C102").customer
    assert baseline is not None

    alias = tools.customer_information("C102").customer
    assert alias == baseline

    by_email = tools.lookup_customer(baseline.email).customer
    assert by_email == baseline

    by_name = tools.find_customer(baseline.name).customer
    assert by_name == baseline

    details = tools.get_customer_details("C102").customer
    assert details is not None
    for field, value in baseline.model_dump().items():
        assert getattr(details, field) == value


def test_customer_details_is_a_strict_superset() -> None:
    baseline = tools.get_customer("C107").customer
    details = tools.get_customer_details("C107").customer
    assert baseline is not None and details is not None
    assert set(baseline.model_dump()) < set(details.model_dump())


@pytest.mark.parametrize(
    ("field_lookup", "value"),
    [("find_customer", "yuki tanabe"), ("lookup_customer", "PRIYA.R@EXAMPLE.TEST")],
)
def test_name_and_email_lookups_are_case_insensitive(field_lookup: str, value: str) -> None:
    result = TOOL_DEFINITIONS[field_lookup].fn(value)
    assert result.found is True


def test_search_is_ordered_by_id_and_unranked() -> None:
    result = tools.search_customers("example.test")
    assert result.match_count == 12
    ids = [c.customer_id for c in result.customers]
    assert ids == sorted(ids)


def test_search_with_no_match_returns_empty_not_everything() -> None:
    assert tools.search_customers("zzzznomatch").match_count == 0


def test_blank_search_matches_nothing() -> None:
    assert tools.search_customers("   ").match_count == 0


@pytest.mark.parametrize("module_name", ["models", "data", "tools", "toolspaces"])
def test_pure_layer_never_imports_mcp(module_name: str) -> None:
    """Enforce the architectural seam statically, by parsing the module's imports.

    If the deterministic layer could reach MCP, "testable without transport" would be a claim
    rather than a guarantee, and a later trace could not cleanly separate an environment fault
    from a protocol fault.
    """
    source = files("agent_lab.synthetic").joinpath(f"{module_name}.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module.split(".")[0])
    assert "mcp" not in imported, f"{module_name}.py must not import mcp"
