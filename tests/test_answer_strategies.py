"""Deterministic answer-evaluation strategies (`SPEC.md` s9.3, v2.2).

v2.2 forbids one permissive generic substring rule for every answer type. Each strategy is
tested for what it accepts *and* what it rejects, because a matcher that never rejects would
silently inflate task success.
"""

import pytest

from agent_lab.evals.answers import evaluate_answer, normalize


def test_normalization_is_case_and_whitespace_insensitive() -> None:
    assert normalize("  The   Answer.  ") == "the   answer".replace("   ", " ")


@pytest.mark.parametrize(
    ("answer", "expected", "ok"),
    [
        ("active", {"value": "active"}, True),
        ("Active.", {"value": "active"}, True),
        ("the status is active", {"value": "active"}, False),
        ("suspended", {"value": "active"}, False),
    ],
)
def test_exact_match(answer: str, expected: dict[str, object], ok: bool) -> None:
    assert evaluate_answer("exact_match", answer, expected)[0] is ok


@pytest.mark.parametrize(
    ("answer", "expected", "ok"),
    [
        ("The email is priya.r@example.test.", {"email": "priya.r@example.test"}, True),
        ("Lagos", {"city": "Lagos"}, True),
        ("They are in Lisbon.", {"city": "Lagos"}, False),
        ("Lagos", {"city": "Lagos", "status": "active"}, False),
    ],
)
def test_contains_facts(answer: str, expected: dict[str, object], ok: bool) -> None:
    assert evaluate_answer("contains_facts", answer, expected)[0] is ok


@pytest.mark.parametrize(
    ("answer", "expected", "ok"),
    [
        ("The amount due is $391.10.", {"value": 391.10, "type": "number"}, True),
        ("391.1", {"value": 391.10, "type": "number"}, True),
        ("1,391.10 total", {"value": 1391.10, "type": "number"}, True),
        ("The amount due is $39.11.", {"value": 391.10, "type": "number"}, False),
        ("nothing numeric here", {"value": 391.10, "type": "number"}, False),
        ("true", {"value": True, "type": "boolean"}, True),
        ("false", {"value": True, "type": "boolean"}, False),
    ],
)
def test_typed_scalar(answer: str, expected: dict[str, object], ok: bool) -> None:
    assert evaluate_answer("typed_scalar", answer, expected)[0] is ok


def test_a_run_with_no_final_answer_never_succeeds() -> None:
    for strategy, expected in (
        ("exact_match", {"value": "x"}),
        ("contains_facts", {"a": "x"}),
        ("typed_scalar", {"value": 1, "type": "number"}),
    ):
        ok, detail = evaluate_answer(strategy, None, expected)
        assert ok is False
        assert "no final answer" in detail


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(KeyError, match="unknown answer strategy"):
        evaluate_answer("regex_ish", "x", {"value": "x"})


def test_strategies_validate_their_expected_shape() -> None:
    """A malformed expectation must fail loudly rather than evaluate to something."""
    with pytest.raises(ValueError, match="exactly one expected key"):
        evaluate_answer("exact_match", "x", {"a": 1, "b": 2})
    with pytest.raises(ValueError, match="at least one expected fact"):
        evaluate_answer("contains_facts", "x", {})
    with pytest.raises(ValueError, match="'value' and 'type'"):
        evaluate_answer("typed_scalar", "x", {"value": 1})
