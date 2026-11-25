"""007 metric names/units/denominators and bounded dimensions, independent of live delivery."""

import pytest
from ecs_ec.observability.queries import CATALOG, DIMENSIONS, metric_query


def test_names_units_and_separate_denominators():
    """Logical attempts, executions, generations, positions, files and milliseconds cannot be conflated."""
    assert CATALOG["operations_total"] == ("operations", "logical")
    assert CATALOG["attempt_executions_total"] == ("executions", "execution.completed")
    assert CATALOG["records_accepted"] == ("records", "reception.completed")
    assert CATALOG["report_generations_admitted"] == ("generations", "report.admitted")
    assert CATALOG["processing_duration_p95_ms"][0] == "milliseconds"
    assert DIMENSIONS == (
        "service_name",
        "environment",
        "operation",
        "outcome",
        "severity",
    )
    logical = metric_query(
        "unexpected_error_percent", "test", "reception.accept", 30000
    )
    execution = metric_query(
        "execution_unexpected_error_percent", "test", "reception.accept", 30000
    )
    assert "reception.completed" in logical and "execution.completed" not in logical
    assert "execution.completed" in execution and "reception.completed" not in execution
    assert "clamp_min" not in logical and " > 0" in logical
    for name in CATALOG:
        query = metric_query(name, "test", "reception.accept", 30000)
        assert (
            "sum by (trace" not in query
            and "boot_id" not in query
            and "publication_ref" not in query
        )
        assert "| json |" not in query


@pytest.mark.parametrize(
    "name,environment,operation,window",
    [
        ("arbitrary", "test", "cost.query", 1000),
        ("operations_total", "foreign", "cost.query", 1000),
        ("operations_total", "test", "PRIVATE_INPUT", 1000),
        ("operations_total", "test", "cost.query", 86400001),
        ("operations_total", "test", "cost.query", True),
    ],
)
def test_unknown_selections_fail_before_query(name, environment, operation, window):
    """No free selector/dimension/window can enter a generated technical query."""
    with pytest.raises(ValueError):
        metric_query(name, environment, operation, window)
