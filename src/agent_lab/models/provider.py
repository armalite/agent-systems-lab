"""Paid-execution authorization, request budgets, and secret redaction.

Three independent safeguards, none of which is satisfied by having credentials configured
(`SPEC.md` s19):

1. **Authorization** - a paid adapter refuses to run unless the operator explicitly opted in for
   this invocation (`agent-lab run --allow-paid`).
2. **Budget** - a hard ceiling on provider requests, declared in the experiment config and
   enforced at call time. Exceeding it aborts rather than continuing to spend.
3. **Redaction** - credentials are never passed through config, CLI, trace, or result, and a
   deterministic scrub runs over everything persisted as a last line of defence.
"""

import re
from typing import Any, cast

SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)
REDACTED = "[REDACTED]"

PAID_PROVIDERS = frozenset({"anthropic"})
"""Providers whose calls can incur cost. `fake` is absent by design."""


class PaidExecutionNotAuthorizedError(RuntimeError):
    """Raised when a cost-incurring call is attempted without explicit run-time opt-in."""


class RequestBudgetExceededError(RuntimeError):
    """Raised when a run would exceed the configured provider-request ceiling."""


class PaidExecutionGate:
    """Guards every cost-incurring provider request.

    Constructed by the runner from the experiment config and the `--allow-paid` flag. The
    presence of `ANTHROPIC_API_KEY` is never consulted: credentials authorize nothing.
    """

    def __init__(self, *, provider: str, authorized: bool, max_requests: int | None) -> None:
        self._provider = provider
        self._authorized = authorized
        self._max_requests = max_requests
        self._used = 0

    @property
    def is_paid(self) -> bool:
        return self._provider in PAID_PROVIDERS

    @property
    def requests_used(self) -> int:
        return self._used

    @property
    def max_requests(self) -> int | None:
        return self._max_requests

    def authorize(self) -> None:
        """Check the run is permitted to spend at all. Called before any client is built."""
        if not self.is_paid:
            return
        if not self._authorized:
            raise PaidExecutionNotAuthorizedError(
                f"provider {self._provider!r} can incur cost and was not authorized for this "
                "run. Pass --allow-paid to authorize it explicitly. Configured credentials do "
                "not authorize paid execution."
            )
        if self._max_requests is None:
            raise PaidExecutionNotAuthorizedError(
                f"provider {self._provider!r} requires cost_controls.max_provider_requests to "
                "be declared in the experiment config."
            )

    def consume(self) -> None:
        """Account for one provider request, refusing to exceed the declared ceiling."""
        self.authorize()
        if not self.is_paid:
            return
        if self._max_requests is not None and self._used >= self._max_requests:
            raise RequestBudgetExceededError(
                f"provider request budget exhausted: {self._used} of {self._max_requests} used. "
                "Raise cost_controls.max_provider_requests deliberately if more are intended."
            )
        self._used += 1


def redact(value: Any) -> Any:
    """Recursively replace anything shaped like a credential.

    Deterministic, so redaction never makes two otherwise-identical traces differ.
    """
    if isinstance(value, str):
        scrubbed = value
        for pattern in SECRET_PATTERNS:
            scrubbed = pattern.sub(REDACTED, scrubbed)
        return scrubbed
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        return {key: redact(item) for key, item in mapping.items()}
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [redact(item) for item in items]
    if isinstance(value, tuple):
        entries = cast(tuple[Any, ...], value)
        return tuple(redact(item) for item in entries)
    return value


class ProviderCallError(RuntimeError):
    """A provider request failed. Recorded as evidence; the run aborts rather than replaying.

    Replaying a failed turn could produce a different tool-call trajectory, which would make the
    substantive-call sequence ambiguous (`SPEC.md` s12).
    """

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
