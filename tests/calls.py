"""Shared call tables so the direct and MCP acceptance tests exercise the same invocations.

Kept here rather than imported from another test module: both `test_synthetic_tools.py` and
`test_mcp_server.py` need them, and comparing the two paths is only meaningful if the calls are
identical.
"""

from typing import Any

# One valid call per tool, covering every tool in both tool-spaces.
VALID_CALLS: dict[str, dict[str, Any]] = {
    "get_customer": {"customer_id": "C102"},
    "get_order": {"order_id": "O204"},
    "get_invoice": {"invoice_id": "I301"},
    "get_product": {"product_id": "P502"},
    "get_employee": {"employee_id": "E104"},
    "find_customer": {"name": "Yuki Tanabe"},
    "search_customers": {"query": "Auckland"},
    "get_customer_details": {"customer_id": "C102"},
    "lookup_customer": {"email": "priya.r@example.test"},
    "customer_information": {"customer_id": "C102"},
}

# Identifiers that are absent from the fixtures, for not-found behaviour.
MISSING_CALLS: dict[str, dict[str, Any]] = {
    "get_customer": {"customer_id": "C999"},
    "get_order": {"order_id": "O999"},
    "get_invoice": {"invoice_id": "I999"},
    "get_product": {"product_id": "P999"},
    "get_employee": {"employee_id": "E999"},
    "find_customer": {"name": "Nobody Here"},
    "get_customer_details": {"customer_id": "C999"},
    "lookup_customer": {"email": "nobody@example.test"},
    "customer_information": {"customer_id": "C999"},
}
