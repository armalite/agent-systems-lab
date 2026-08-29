"""Cost control is a hard requirement (SPEC.md s19), so it is tested, not merely configured.

Default test runs must never make a paid model-provider API call. The `paid` marker exists so
that provider-hitting tests can only ever run when a human explicitly selects them.
"""

import pytest


def test_paid_gate_is_configured_as_the_default(pytestconfig: pytest.Config) -> None:
    """Pin the configured default, not the current run's options.

    Asserting the resolved `-m` expression would fail for any legitimate custom selection
    (e.g. `-m "not paid and not slow"`), which invites a future contributor to weaken the gate
    to make tests pass. The durable invariant is what `pyproject.toml` sets by default.
    """
    addopts = pytestconfig.getini("addopts")
    assert "--strict-markers" in addopts, "unregistered/typo'd markers must be an error"
    assert "-m" in addopts and "not paid" in addopts, (
        "the default marker expression must exclude paid tests"
    )


@pytest.mark.paid
def test_paid_marker_actually_gates_collection(pytestconfig: pytest.Config) -> None:
    """End-to-end tripwire on the `paid` gate.

    Reaching this test while the run excludes paid tests means the gate has broken. Reaching it
    under an explicit opt-in (`-m paid`) is correct, and the test skips: Milestone 0 has no
    provider integration, so there is nothing billable to exercise yet.

    Its `@pytest.mark.paid` decorator also exercises marker registration - under
    `--strict-markers` an unregistered marker fails collection here.
    """
    markexpr = pytestconfig.getoption("markexpr")
    if not markexpr or "not paid" in markexpr:
        pytest.fail(
            "A test marked `paid` ran without being explicitly selected "
            f"(marker expression: {markexpr!r}). Either the default deselection was removed or "
            "the gate is broken. Paid provider calls must remain opt-in only (see AGENTS.md s6)."
        )
    pytest.skip("Paid tests explicitly selected, but no provider integration exists yet (M0).")
