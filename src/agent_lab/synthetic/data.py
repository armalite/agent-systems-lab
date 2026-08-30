"""Fixture loading and indexing. Pure Python - no MCP, no network, no clock, no randomness.

Fixture values are fixed literals checked into the repository and are deliberately **not
derivable from their identifiers**. If an answer could be guessed from the key alone, a task
would measure guessing rather than tool use.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

from agent_lab.synthetic.models import (
    Customer,
    CustomerDetails,
    Employee,
    Invoice,
    Order,
    Product,
)

FIXTURE_FILES = (
    "customers.json",
    "orders.json",
    "invoices.json",
    "products.json",
    "employees.json",
)


def _read_fixture(filename: str) -> list[dict[str, Any]]:
    source = files("agent_lab.synthetic.fixtures").joinpath(filename)
    parsed: object = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError(f"fixture {filename} must contain a JSON array")
    rows: list[dict[str, Any]] = []
    for item in cast(list[object], parsed):
        if not isinstance(item, dict):
            raise ValueError(f"fixture {filename} must contain only JSON objects")
        rows.append(cast(dict[str, Any], item))
    return rows


@dataclass(frozen=True)
class Dataset:
    """Immutable, fully indexed fixture data.

    Records are stored in `customer_id`-sorted order so that any operation returning multiple
    results is deterministic without needing to sort at call time.
    """

    customers: tuple[CustomerDetails, ...]
    orders: tuple[Order, ...]
    invoices: tuple[Invoice, ...]
    products: tuple[Product, ...]
    employees: tuple[Employee, ...]

    def customer_by_id(self, customer_id: str) -> CustomerDetails | None:
        return next((c for c in self.customers if c.customer_id == customer_id), None)

    def customer_by_name(self, name: str) -> CustomerDetails | None:
        """Case-insensitive exact full-name match. Names are unique in the fixture set."""
        needle = name.strip().casefold()
        return next((c for c in self.customers if c.name.casefold() == needle), None)

    def customer_by_email(self, email: str) -> CustomerDetails | None:
        """Case-insensitive exact email match. Emails are unique in the fixture set."""
        needle = email.strip().casefold()
        return next((c for c in self.customers if c.email.casefold() == needle), None)

    def search_customers(self, query: str) -> tuple[CustomerDetails, ...]:
        """Case-insensitive substring match over name, email, and city.

        Deliberately not a ranked search: matches are returned in `customer_id` order. Relevance
        ranking would introduce a hidden variable into an environment that must be fully
        controlled. An empty or whitespace-only query matches nothing rather than everything.
        """
        needle = query.strip().casefold()
        if not needle:
            return ()
        return tuple(
            c
            for c in self.customers
            if needle in c.name.casefold()
            or needle in c.email.casefold()
            or needle in c.city.casefold()
        )

    def order_by_id(self, order_id: str) -> Order | None:
        return next((o for o in self.orders if o.order_id == order_id), None)

    def invoice_by_id(self, invoice_id: str) -> Invoice | None:
        return next((i for i in self.invoices if i.invoice_id == invoice_id), None)

    def product_by_id(self, product_id: str) -> Product | None:
        return next((p for p in self.products if p.product_id == product_id), None)

    def employee_by_id(self, employee_id: str) -> Employee | None:
        return next((e for e in self.employees if e.employee_id == employee_id), None)


def _check_integrity(dataset: Dataset) -> None:
    """Fail loudly on fixture corruption rather than silently serving broken data."""
    customer_ids = {c.customer_id for c in dataset.customers}
    employee_ids = {e.employee_id for e in dataset.employees}
    order_ids = {o.order_id for o in dataset.orders}

    for label, ids, records in (
        ("customer", customer_ids, dataset.customers),
        ("employee", employee_ids, dataset.employees),
        ("order", order_ids, dataset.orders),
    ):
        if len(ids) != len(records):
            raise ValueError(f"duplicate {label} identifiers in fixtures")

    names = {c.name.casefold() for c in dataset.customers}
    emails = {c.email.casefold() for c in dataset.customers}
    if len(names) != len(dataset.customers):
        raise ValueError("customer names must be unique for find_customer to be deterministic")
    if len(emails) != len(dataset.customers):
        raise ValueError("customer emails must be unique for lookup_customer to be deterministic")

    for customer in dataset.customers:
        if customer.account_manager_id not in employee_ids:
            raise ValueError(f"{customer.customer_id} references unknown employee")
    for order in dataset.orders:
        if order.customer_id not in customer_ids:
            raise ValueError(f"{order.order_id} references unknown customer")
    for invoice in dataset.invoices:
        if invoice.order_id not in order_ids:
            raise ValueError(f"{invoice.invoice_id} references unknown order")
        if invoice.customer_id not in customer_ids:
            raise ValueError(f"{invoice.invoice_id} references unknown customer")


@lru_cache(maxsize=1)
def load_dataset() -> Dataset:
    """Load, validate, and cache the fixture dataset.

    Cached because the data is immutable and identical for every call; this keeps repeated
    tool invocations byte-identical without re-reading files.
    """
    dataset = Dataset(
        customers=tuple(
            sorted(
                (CustomerDetails(**row) for row in _read_fixture("customers.json")),
                key=lambda c: c.customer_id,
            )
        ),
        orders=tuple(
            sorted((Order(**row) for row in _read_fixture("orders.json")), key=lambda o: o.order_id)
        ),
        invoices=tuple(
            sorted(
                (Invoice(**row) for row in _read_fixture("invoices.json")),
                key=lambda i: i.invoice_id,
            )
        ),
        products=tuple(
            sorted(
                (Product(**row) for row in _read_fixture("products.json")),
                key=lambda p: p.product_id,
            )
        ),
        employees=tuple(
            sorted(
                (Employee(**row) for row in _read_fixture("employees.json")),
                key=lambda e: e.employee_id,
            )
        ),
    )
    _check_integrity(dataset)
    return dataset


def to_core_customer(details: CustomerDetails) -> Customer:
    """Project the stored record down to the core `Customer` view.

    Single source of truth: `get_customer` and `get_customer_details` read the same stored
    record, so the overlapping tools cannot drift out of agreement.
    """
    return Customer(
        customer_id=details.customer_id,
        name=details.name,
        email=details.email,
        city=details.city,
        status=details.status,
    )
