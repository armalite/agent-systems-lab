# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false
#
# pyarrow and duckdb ship no type information, so every call through them is Unknown to a
# strict checker. The suppression is confined to the two modules that touch those libraries
# rather than relaxing strict mode across the project.
"""Parquet persistence and direct DuckDB queryability.

`SPEC.md` s13 requires DuckDB to work against results without application code. This proves it
without building any analysis tooling - that is Milestone 5.
"""

import duckdb
import pytest

from agent_lab.storage.parquet import RESULT_SCHEMA, read_results
from tests.harness import Execution, execute


@pytest.fixture(scope="module")
def execution(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    return execute(tmp_path_factory.mktemp("storage"))


def test_parquet_uses_the_declared_schema(execution: Execution) -> None:
    import pyarrow.parquet as pq

    paths, _ = execution
    assert pq.read_table(paths.results).schema.equals(RESULT_SCHEMA)


def test_parquet_roundtrips_every_row(execution: Execution) -> None:
    paths, rows = execution
    assert len(read_results(paths.results)) == len(rows)


def test_nullable_fields_survive_as_null(execution: Execution) -> None:
    paths, _ = execution
    records = read_results(paths.results)
    assert any(record["tool_recovery_success"] is None for record in records)
    assert all(record["input_tokens"] is None for record in records)


def test_duckdb_queries_the_parquet_without_application_code(execution: Execution) -> None:
    paths, rows = execution
    con = duckdb.connect()
    total = con.execute("SELECT count(*) FROM read_parquet(?)", [str(paths.results)]).fetchone()
    assert total is not None and total[0] == len(rows)


def test_duckdb_can_unnest_the_tool_call_sequence(execution: Execution) -> None:
    """The reason `tool_call_sequence` is a list<struct> rather than a JSON blob."""
    paths, _ = execution
    con = duckdb.connect()
    result = con.execute(
        """
        SELECT call.name AS tool_name, count(*) AS n
        FROM read_parquet(?), UNNEST(tool_call_sequence) AS t(call)
        GROUP BY call.name
        ORDER BY n DESC, tool_name
        """,
        [str(paths.results)],
    ).fetchall()
    names = {row[0] for row in result}
    assert "get_customer" in names
    assert "fetch_employee_record" in names, "unknown-tool attempts must remain queryable"


def test_duckdb_can_compare_conditions(execution: Execution) -> None:
    """The shape of question the lab exists to answer, answered with plain SQL."""
    paths, _ = execution
    con = duckdb.connect()
    rows = con.execute(
        """
        SELECT tool_space_id,
               sum(CASE WHEN first_call_routing_correct THEN 1 ELSE 0 END) AS routed,
               count(*) AS n
        FROM read_parquet(?)
        GROUP BY tool_space_id
        ORDER BY tool_space_id
        """,
        [str(paths.results)],
    ).fetchall()
    assert len(rows) == 2
    assert all(row[2] == 16 for row in rows)
