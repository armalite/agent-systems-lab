# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false
#
# pyarrow and duckdb ship no type information, so every call through them is Unknown to a
# strict checker. The suppression is confined to the two modules that touch those libraries
# rather than relaxing strict mode across the project.
"""Parquet persistence with an explicit schema.

The schema is declared rather than inferred, so a column type can never silently change between
executions. `tool_call_sequence` is a `list<struct>` so DuckDB can `UNNEST` it natively without
any application code (`SPEC.md` s13).

Unknown values are written as null, never as zero. A fake adapter reports no token usage, and
recording that as `0` would be a fabricated measurement.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from agent_lab.experiments.result import ResultRow

TOOL_CALL_STRUCT = pa.struct(
    [
        pa.field("sequence", pa.int32()),
        pa.field("name", pa.string()),
        pa.field("arguments_json", pa.string()),
        pa.field("ok", pa.bool_()),
        pa.field("error_kind", pa.string()),
    ]
)

RESULT_SCHEMA = pa.schema(
    [
        pa.field("run_id", pa.string()),
        pa.field("execution_id", pa.string()),
        pa.field("experiment_id", pa.string()),
        pa.field("experiment_classification", pa.string()),
        pa.field("timestamp", pa.string()),
        pa.field("source_commit_sha", pa.string()),
        pa.field("source_tree_dirty", pa.bool_()),
        pa.field("harness_version", pa.string()),
        pa.field("trace_schema_version", pa.string()),
        pa.field("result_schema_version", pa.string()),
        pa.field("metric_definition_id", pa.string()),
        pa.field("metric_definition_fingerprint", pa.string()),
        pa.field("config_fingerprint", pa.string()),
        pa.field("task_set_fingerprint", pa.string()),
        pa.field("provider", pa.string()),
        pa.field("model", pa.string()),
        pa.field("model_parameters", pa.string()),
        pa.field("environment_id", pa.string()),
        pa.field("environment_version", pa.string()),
        pa.field("environment_fingerprint", pa.string()),
        pa.field("model_surface_fingerprint", pa.string()),
        pa.field("provider_surface_fingerprint", pa.string()),
        pa.field("model_requested", pa.string()),
        pa.field("model_served", pa.string()),
        pa.field("model_snapshot_available", pa.bool_()),
        pa.field("model_controls", pa.string()),
        pa.field("provider_request_ids", pa.list_(pa.string())),
        pa.field("provider_stop_reason", pa.string()),
        pa.field("provider_error_kind", pa.string()),
        pa.field("task_id", pa.string()),
        pa.field("task_set", pa.string()),
        pa.field("tool_space_id", pa.string()),
        pa.field("tool_count", pa.int32()),
        pa.field("tool_names", pa.list_(pa.string())),
        pa.field("expected_tool", pa.string()),
        pa.field("expected_arguments", pa.string()),
        pa.field("tool_call_sequence", pa.list_(TOOL_CALL_STRUCT)),
        pa.field("first_tool", pa.string()),
        pa.field("first_tool_arguments", pa.string()),
        pa.field("first_tool_correct", pa.bool_()),
        pa.field("first_tool_arguments_correct", pa.bool_()),
        pa.field("first_call_routing_correct", pa.bool_()),
        pa.field("expected_tool_used", pa.bool_()),
        pa.field("expected_tool_used_correctly", pa.bool_()),
        pa.field("incorrect_tool_call_count", pa.int32()),
        pa.field("unnecessary_tool_call_count", pa.int32()),
        pa.field("tool_recovery_success", pa.bool_()),
        pa.field("expected_answer", pa.string()),
        pa.field("actual_answer", pa.string()),
        pa.field("answer_strategy", pa.string()),
        pa.field("answer_detail", pa.string()),
        pa.field("task_success", pa.bool_()),
        pa.field("stop_reason", pa.string()),
        pa.field("tool_call_count", pa.int32()),
        pa.field("input_tokens", pa.int64()),
        pa.field("output_tokens", pa.int64()),
        pa.field("latency_ms", pa.float64()),
        pa.field("repetition", pa.int32()),
        pa.field("random_seed_if_applicable", pa.int64()),
        pa.field("trace_path", pa.string()),
    ]
)


def _row_to_dict(row: ResultRow) -> dict[str, Any]:
    data = row.model_dump(mode="json")
    data["tool_names"] = list(row.tool_names)
    data["provider_request_ids"] = list(row.provider_request_ids)
    data["tool_call_sequence"] = [call.model_dump(mode="json") for call in row.tool_call_sequence]
    return data


def write_results(path: Path, rows: Sequence[ResultRow]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [_row_to_dict(row) for row in rows]
    columns = {
        field.name: [record.get(field.name) for record in records] for field in RESULT_SCHEMA
    }
    table = pa.Table.from_pydict(columns, schema=RESULT_SCHEMA)
    pq.write_table(table, path)
    return path


def read_results(path: Path) -> list[dict[str, Any]]:
    return pq.read_table(path).to_pylist()
