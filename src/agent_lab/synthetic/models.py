"""Typed records and result envelopes returned by the synthetic tools.

Every tool returns a structured envelope rather than raising on a miss: a "not found" is a
legitimate, deterministic answer, and it must stay distinguishable from a transport or
protocol failure once tracing exists (Milestone 2).
"""

from pydantic import BaseModel, ConfigDict


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Customer(_Record):
    """A customer account."""

    customer_id: str
    name: str
    email: str
    city: str
    status: str


# NOTE: docstrings on these models are serialized into the MCP output schema and are visible
# to the model. Keep them neutral API prose. Experimental rationale belongs in comments like
# this one: CustomerDetails is a strict superset of Customer, projected from the same stored
# record, so the overlapping tools can never contradict the baseline ones.
class CustomerDetails(_Record):
    """A customer account, including account-management detail."""

    customer_id: str
    name: str
    email: str
    city: str
    status: str
    phone: str
    segment: str
    account_manager_id: str
    created_on: str


class Order(_Record):
    order_id: str
    customer_id: str
    status: str
    total_amount: float
    currency: str
    placed_on: str
    item_count: int


class Invoice(_Record):
    invoice_id: str
    order_id: str
    customer_id: str
    amount_due: float
    currency: str
    status: str
    issued_on: str
    due_on: str


class Product(_Record):
    product_id: str
    name: str
    category: str
    price: float
    currency: str
    sku: str
    in_stock: bool


class Employee(_Record):
    employee_id: str
    name: str
    role: str
    office: str
    email: str


class CustomerResult(_Record):
    found: bool
    customer: Customer | None = None
    message: str | None = None


class CustomerDetailsResult(_Record):
    found: bool
    customer: CustomerDetails | None = None
    message: str | None = None


class CustomerSearchResult(_Record):
    """Matching customers, ordered by customer ID."""

    match_count: int
    customers: tuple[Customer, ...] = ()


class OrderResult(_Record):
    found: bool
    order: Order | None = None
    message: str | None = None


class InvoiceResult(_Record):
    found: bool
    invoice: Invoice | None = None
    message: str | None = None


class ProductResult(_Record):
    found: bool
    product: Product | None = None
    message: str | None = None


class EmployeeResult(_Record):
    found: bool
    employee: Employee | None = None
    message: str | None = None
