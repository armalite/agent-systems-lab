"""Deterministic answer-evaluation strategies.

`SPEC.md` s9.3 forbids one permissive generic substring rule applied to every answer type. Each
task declares its strategy, and the strategy plus its expected facts are frozen experimental
material - part of the task definition, fixed before results are observed.

The set is deliberately small. Add a strategy only when a task genuinely needs it, and never
loosen an existing one to make a result pass.
"""

import re
from collections.abc import Callable, Mapping
from typing import Any

STRATEGY_EXACT_MATCH = "exact_match"
STRATEGY_CONTAINS_FACTS = "contains_facts"
STRATEGY_TYPED_SCALAR = "typed_scalar"

_WHITESPACE = re.compile(r"\s+")
_NUMERIC_TOKEN = re.compile(r"-?\d+(?:\.\d+)?")


def normalize(text: str) -> str:
    """Casefold, collapse whitespace, strip surrounding punctuation and space."""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    return collapsed.strip(" .,;:!?\"'").casefold()


def _render(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _exact_match(answer: str, expected: Mapping[str, Any]) -> tuple[bool, str]:
    """The whole normalized answer must equal the normalized expected `value`."""
    if set(expected) != {"value"}:
        raise ValueError("exact_match expects exactly one expected key: 'value'")
    want = normalize(_render(expected["value"]))
    got = normalize(answer)
    return got == want, f"exact_match: expected {want!r}, got {got!r}"


def _contains_facts(answer: str, expected: Mapping[str, Any]) -> tuple[bool, str]:
    """Every expected fact value must appear in the normalized answer."""
    if not expected:
        raise ValueError("contains_facts requires at least one expected fact")
    got = normalize(answer)
    missing = [key for key, value in expected.items() if normalize(_render(value)) not in got]
    return not missing, f"contains_facts: missing {missing}" if missing else "contains_facts: all"


def _typed_scalar(answer: str, expected: Mapping[str, Any]) -> tuple[bool, str]:
    """Compare a scalar by type rather than by string shape.

    For numbers, every numeric token in the answer is extracted and the expected value must be
    among them under exact decimal comparison - so "391.10" matches "The amount due is $391.10."
    but not "39.11". Digit grouping separators are removed before extraction.
    """
    if set(expected) != {"value", "type"}:
        raise ValueError("typed_scalar expects exactly the keys 'value' and 'type'")
    declared = expected["type"]
    if declared in {"number", "integer"}:
        candidates = _NUMERIC_TOKEN.findall(answer.replace(",", ""))
        want = float(expected["value"])
        found = [float(token) for token in candidates]
        return any(value == want for value in found), (
            f"typed_scalar[{declared}]: expected {want}, found {found}"
        )
    if declared == "boolean":
        got = normalize(answer)
        want_word = _render(bool(expected["value"]))
        return want_word in got.split(), f"typed_scalar[boolean]: expected {want_word!r}"
    if declared == "string":
        return _exact_match(answer, {"value": expected["value"]})
    raise ValueError(f"unknown typed_scalar type {declared!r}")


ANSWER_STRATEGIES: dict[str, Callable[[str, Mapping[str, Any]], tuple[bool, str]]] = {
    STRATEGY_EXACT_MATCH: _exact_match,
    STRATEGY_CONTAINS_FACTS: _contains_facts,
    STRATEGY_TYPED_SCALAR: _typed_scalar,
}


def evaluate_answer(
    strategy: str, answer: str | None, expected: Mapping[str, Any]
) -> tuple[bool, str]:
    """Apply a declared strategy. A run with no final answer never succeeds."""
    if strategy not in ANSWER_STRATEGIES:
        raise KeyError(f"unknown answer strategy {strategy!r}; known: {sorted(ANSWER_STRATEGIES)}")
    if answer is None:
        return False, f"{strategy}: no final answer was produced"
    return ANSWER_STRATEGIES[strategy](answer, expected)
