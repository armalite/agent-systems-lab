"""Fixture integrity and indexing. No MCP involved."""

import json
from importlib.resources import files
from typing import cast

import pytest

from agent_lab.synthetic.data import FIXTURE_FILES, load_dataset, to_core_customer

# Expanded for Phase 0: the customer stratum carries the primary paired comparison and needs one
# task per distinct record, so customers were grown to 20 before the task set was frozen
# (`SPEC.md` s16, v2.5 - fixture material may be expanded while the design is still open).
EXPECTED_FIXTURE_COUNTS = {
    "customers.json": 20,
    "orders.json": 12,
    "invoices.json": 12,
    "products.json": 12,
    "employees.json": 12,
}


def test_all_fixture_files_are_present_and_populated() -> None:
    assert set(EXPECTED_FIXTURE_COUNTS) == set(FIXTURE_FILES)
    for filename in FIXTURE_FILES:
        raw = files("agent_lab.synthetic.fixtures").joinpath(filename).read_text(encoding="utf-8")
        records: object = json.loads(raw)
        assert isinstance(records, list)
        expected = EXPECTED_FIXTURE_COUNTS[filename]
        assert len(cast(list[object], records)) == expected, (
            f"{filename} should hold {expected} records"
        )


def test_dataset_loads_and_passes_integrity_checks() -> None:
    dataset = load_dataset()
    assert len(dataset.customers) == 20
    assert len(dataset.orders) == 12
    assert len(dataset.invoices) == 12
    assert len(dataset.products) == 12
    assert len(dataset.employees) == 12


def test_records_are_sorted_by_identifier() -> None:
    """Stable ordering is what makes multi-result operations deterministic."""
    dataset = load_dataset()
    assert [c.customer_id for c in dataset.customers] == sorted(
        c.customer_id for c in dataset.customers
    )
    assert [o.order_id for o in dataset.orders] == sorted(o.order_id for o in dataset.orders)


def test_customer_names_and_emails_are_unique() -> None:
    """find_customer and lookup_customer are only deterministic if these are unique."""
    dataset = load_dataset()
    assert len({c.name.casefold() for c in dataset.customers}) == len(dataset.customers)
    assert len({c.email.casefold() for c in dataset.customers}) == len(dataset.customers)


def test_referential_integrity_holds() -> None:
    dataset = load_dataset()
    customer_ids = {c.customer_id for c in dataset.customers}
    employee_ids = {e.employee_id for e in dataset.employees}
    order_ids = {o.order_id for o in dataset.orders}

    assert all(o.customer_id in customer_ids for o in dataset.orders)
    assert all(c.account_manager_id in employee_ids for c in dataset.customers)
    assert all(i.order_id in order_ids for i in dataset.invoices)
    assert all(i.customer_id in customer_ids for i in dataset.invoices)


def test_invoice_customer_agrees_with_its_order() -> None:
    dataset = load_dataset()
    order_customer = {o.order_id: o.customer_id for o in dataset.orders}
    for invoice in dataset.invoices:
        assert invoice.customer_id == order_customer[invoice.order_id]


@pytest.mark.parametrize("customer_id", ["C101", "C102", "C107", "C112", "C115", "C120"])
def test_fixture_values_are_not_derivable_from_identifiers(customer_id: str) -> None:
    """An answer inferable from the key alone would measure guessing, not tool use."""
    record = load_dataset().customer_by_id(customer_id)
    assert record is not None
    digits = customer_id[1:]
    assert digits not in record.email
    assert digits not in record.name
    assert customer_id.casefold() not in record.email.casefold()


def test_fixtures_use_only_reserved_test_domain() -> None:
    dataset = load_dataset()
    assert all(c.email.endswith("@example.test") for c in dataset.customers)
    assert all(e.email.endswith("@example.test") for e in dataset.employees)


def test_core_projection_preserves_shared_fields() -> None:
    """The baseline and overlap views of a customer come from one stored record."""
    for details in load_dataset().customers:
        core = to_core_customer(details)
        assert core.customer_id == details.customer_id
        assert core.name == details.name
        assert core.email == details.email
        assert core.city == details.city
        assert core.status == details.status
