"""Pure synthetic tool implementations. **This module must not import `mcp`.**

Every function is a deterministic pure lookup over the checked-in fixture dataset: no clock, no
randomness, no network, no I/O beyond the cached fixture load. Identical arguments always yield
identical results, which is what makes the environment's determinism provable independently of
the transport.

The overlapping customer tools are genuinely functional and internally consistent with the
baseline tools: they read the same stored records, so choosing an overlapping tool never
produces contradictory data. See this package's `README.md` for the overlap design and its
rationale, recorded before any model experiment is run.
"""

from agent_lab.synthetic.data import load_dataset, to_core_customer
from agent_lab.synthetic.models import (
    CustomerDetailsResult,
    CustomerResult,
    CustomerSearchResult,
    EmployeeResult,
    InvoiceResult,
    OrderResult,
    ProductResult,
)

# ---------------------------------------------------------------------------
# Baseline tools
# ---------------------------------------------------------------------------


def get_customer(customer_id: str) -> CustomerResult:
    record = load_dataset().customer_by_id(customer_id)
    if record is None:
        return CustomerResult(found=False, message=f"No customer with customer_id {customer_id}.")
    return CustomerResult(found=True, customer=to_core_customer(record))


def get_order(order_id: str) -> OrderResult:
    record = load_dataset().order_by_id(order_id)
    if record is None:
        return OrderResult(found=False, message=f"No order with order_id {order_id}.")
    return OrderResult(found=True, order=record)


def get_invoice(invoice_id: str) -> InvoiceResult:
    record = load_dataset().invoice_by_id(invoice_id)
    if record is None:
        return InvoiceResult(found=False, message=f"No invoice with invoice_id {invoice_id}.")
    return InvoiceResult(found=True, invoice=record)


def get_product(product_id: str) -> ProductResult:
    record = load_dataset().product_by_id(product_id)
    if record is None:
        return ProductResult(found=False, message=f"No product with product_id {product_id}.")
    return ProductResult(found=True, product=record)


def get_employee(employee_id: str) -> EmployeeResult:
    record = load_dataset().employee_by_id(employee_id)
    if record is None:
        return EmployeeResult(found=False, message=f"No employee with employee_id {employee_id}.")
    return EmployeeResult(found=True, employee=record)


# ---------------------------------------------------------------------------
# Overlapping calibration tools
# ---------------------------------------------------------------------------


def find_customer(name: str) -> CustomerResult:
    record = load_dataset().customer_by_name(name)
    if record is None:
        return CustomerResult(found=False, message=f"No customer named {name}.")
    return CustomerResult(found=True, customer=to_core_customer(record))


def search_customers(query: str) -> CustomerSearchResult:
    matches = load_dataset().search_customers(query)
    return CustomerSearchResult(
        match_count=len(matches),
        customers=tuple(to_core_customer(record) for record in matches),
    )


def get_customer_details(customer_id: str) -> CustomerDetailsResult:
    record = load_dataset().customer_by_id(customer_id)
    if record is None:
        return CustomerDetailsResult(
            found=False, message=f"No customer with customer_id {customer_id}."
        )
    return CustomerDetailsResult(found=True, customer=record)


def lookup_customer(email: str) -> CustomerResult:
    record = load_dataset().customer_by_email(email)
    if record is None:
        return CustomerResult(found=False, message=f"No customer with email {email}.")
    return CustomerResult(found=True, customer=to_core_customer(record))


def customer_information(customer_id: str) -> CustomerResult:
    record = load_dataset().customer_by_id(customer_id)
    if record is None:
        return CustomerResult(found=False, message=f"No customer with customer_id {customer_id}.")
    return CustomerResult(found=True, customer=to_core_customer(record))
