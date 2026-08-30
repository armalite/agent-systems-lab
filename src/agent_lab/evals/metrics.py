"""Versioned metric definitions.

Metric semantics must not change silently between runs (`SPEC.md` s14). Each definition set is
frozen, named, and carries a canonical specification text; its fingerprint is the hash of that
text together with the ordered metric names. Trace and result rows both record the id and
fingerprint, so rows evaluated under different semantics can never be compared as equivalent.

To change a definition, add a **new** set with a new id. Never edit an existing one in place -
that would silently reinterpret results already on disk.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from agent_lab.environments.surface import fingerprint

PHASE0_SINGLE_TOOL_V1 = "phase0_single_tool_v1"

_PHASE0_SPEC = """\
Metric definitions for simple single-expected-tool tasks (SPEC.md s14, v2.2).

Substantive tool call:
  Any tool invocation emitted by the model, including a call to a tool absent from the
  tool-space and a call whose arguments fail schema validation. Harness-initiated transport
  retries of an identical call are not additional substantive model calls. Calls that cannot be
  attributed to model output are recorded separately and never counted here.

Argument comparison:
  Order-insensitive, exact after canonicalization. Missing expected arguments, incorrect
  values, invalid values, or unexpected extra arguments all make the argument component
  incorrect.

PRIMARY
  first_call_routing_correct:
    The first substantive tool call is the expected tool AND carries exactly the expected
    identifying arguments.

SECONDARY
  first_tool_correct:            first substantive call used the expected tool.
  first_tool_arguments_correct:  first substantive call carried exactly the expected arguments.
  expected_tool_used:            the expected tool appears anywhere in the call sequence.
  expected_tool_used_correctly:  the expected tool appears with exactly the expected arguments.
  tool_recovery_success:         NULL when first_call_routing_correct is true (no recovery was
                                 required); otherwise equal to expected_tool_used_correctly.
  incorrect_tool_call_count:     substantive calls that are not the expected tool with exactly
                                 the expected arguments.
  unnecessary_tool_call_count:   substantive calls occurring after the first correct call to
                                 the expected tool.
  tool_call_count:               total substantive calls.
  task_success:                  the task's declared deterministic answer strategy accepts the
                                 final answer. Independent of tool-use correctness; a run with
                                 no final answer never succeeds.

incorrect_tool_call_count and unnecessary_tool_call_count may overlap; they answer different
questions and are not intended to partition the call sequence.
"""

_PHASE0_METRICS = (
    "first_tool",
    "first_tool_arguments",
    "first_tool_correct",
    "first_tool_arguments_correct",
    "first_call_routing_correct",
    "expected_tool_used",
    "expected_tool_used_correctly",
    "tool_recovery_success",
    "incorrect_tool_call_count",
    "unnecessary_tool_call_count",
    "tool_call_count",
    "task_success",
)


class MetricDefinitionSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    primary_metric: str
    metrics: tuple[str, ...]
    specification: str

    def fingerprint(self) -> str:
        return fingerprint(
            {
                "id": self.id,
                "primary_metric": self.primary_metric,
                "metrics": list(self.metrics),
                "specification": self.specification,
            }
        )

    def provenance(self) -> dict[str, Any]:
        return {
            "metric_definition_id": self.id,
            "metric_definition_fingerprint": self.fingerprint(),
        }


METRIC_DEFINITION_SETS: dict[str, MetricDefinitionSet] = {
    PHASE0_SINGLE_TOOL_V1: MetricDefinitionSet(
        id=PHASE0_SINGLE_TOOL_V1,
        primary_metric="first_call_routing_correct",
        metrics=_PHASE0_METRICS,
        specification=_PHASE0_SPEC,
    )
}
