"""The raw trace event model.

The trace is the source of truth (`SPEC.md` s18: raw trace > normalized row > summary). Every
observable step is one event; nothing is batched, summarized, or dropped at write time.

`layer` makes the four-way separation required by `SPEC.md` s12 queryable rather than inferred,
so a failure can be attributed to the model, the MCP transport, the deterministic tool, or the
evaluator without guessing from event names.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TRACE_SCHEMA_VERSION = "1.2.0"
"""1.1.0 added the `provider` layer and the provider-boundary events (Milestone 3).
1.2.0 adds source-provenance and execution-schedule fields to the `RUN_STARTED` payload
(`schedule_index`, `task_index`, `source_commit_sha`, `source_tree_dirty`), from which the
normalized row derives them. Traces written under 1.0.0/1.1.0 remain readable; the context
field added in 1.1.0 defaults to empty."""

Layer = Literal["harness", "model", "mcp", "tool", "provider", "evaluator"]

RUN_STARTED = "RUN_STARTED"
ENVIRONMENT_CONNECTED = "ENVIRONMENT_CONNECTED"
MODEL_REQUEST = "MODEL_REQUEST"
MODEL_RESPONSE = "MODEL_RESPONSE"
TOOL_CALL_REQUESTED = "TOOL_CALL_REQUESTED"
TOOL_CALL_EXECUTED = "TOOL_CALL_EXECUTED"
TOOL_CALL_FAILED = "TOOL_CALL_FAILED"
TOOL_RESULT_RETURNED = "TOOL_RESULT_RETURNED"
PROVIDER_SURFACE_PREPARED = "PROVIDER_SURFACE_PREPARED"
PROVIDER_ERROR = "PROVIDER_ERROR"
RUN_COMPLETED = "RUN_COMPLETED"
EVALUATION_COMPLETED = "EVALUATION_COMPLETED"

# Fields that legitimately differ between two identical executions. Excluded when comparing
# traces for determinism; never excluded from what is persisted.
VOLATILE_EVENT_FIELDS = frozenset({"timestamp", "execution_id"})
VOLATILE_PAYLOAD_FIELDS = frozenset({"latency_ms", "started_at", "completed_at", "duration_ms"})


class TraceEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_schema_version: str = TRACE_SCHEMA_VERSION
    sequence: int
    timestamp: str
    layer: Layer
    event_type: str

    run_id: str
    execution_id: str
    experiment_id: str
    task_id: str
    repetition: int
    tool_space_id: str
    environment_fingerprint: str
    model_surface_fingerprint: str
    provider_surface_fingerprint: str = ""
    """Empty for adapters with no distinct provider-facing surface, and for 1.0.0 traces."""

    provider: str
    model: str

    payload: dict[str, Any] = Field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        """The event with volatile fields removed, for determinism comparison."""
        data = self.model_dump(mode="json")
        for field in VOLATILE_EVENT_FIELDS:
            data.pop(field, None)
        payload = dict(data.get("payload") or {})
        for field in VOLATILE_PAYLOAD_FIELDS:
            payload.pop(field, None)
        data["payload"] = payload
        return data
