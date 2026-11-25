"""007 closed LogQL catalog; finite UTC cuts and permitted dimensions only, without a query API.

Consumers query the existing authorized technical gateway. Reference IDs are optional
log filters, never metric dimensions. A returned vector alone cannot prove continuity.
"""

import json
from uuid import UUID
from ecs_ec.observability.events import OPERATIONS

DIMENSIONS = ("service_name", "environment", "operation", "outcome", "severity")
CATALOG = {
    "operations_total": ("operations", "logical"),
    "notification_attempts_observed": ("attempts", "notification.delivery.attempt.completed"),
    "notification_scheduler_cycles": ("cycles", "notification.scheduler.tick"),
    "attempt_executions_total": ("executions", "execution.completed"),
    "report_generations_admitted": ("generations", "report.admitted"),
    "unexpected_error_percent": ("percent", "logical"),
    "execution_unexpected_error_percent": ("percent", "execution.completed"),
    "processing_duration_mean_ms": ("milliseconds", "logical"),
    "processing_duration_p50_ms": ("milliseconds", "logical"),
    "processing_duration_p95_ms": ("milliseconds", "logical"),
    **{
        name: ("records", "reception.completed")
        for name in (
            "records_seen",
            "records_accepted",
            "records_invalid",
            "records_duplicate",
            "records_other_rejected",
        )
    },
    **{
        name: ("files", "acquisition.process")
        for name in ("files_seen", "files_parsed", "files_unreadable")
    },
}


def metric_query(name, environment, operation, window_ms, *, boot_id=None):
    """Build a bounded named measure, or reject before interpolation; caller supplies its exact common cut.

    Loki's `(left,right]` range is evaluated at `end_ns-1`, mapping UTC `[start,end)`
    exactly when end-start equals window_ms milliseconds. No current-time default is
    used here. Percentages are meaningful as totals only with separately complete coverage.
    """
    if (
        name not in CATALOG
        or environment not in {"local", "test", "vps"}
        or operation not in OPERATIONS
        or type(window_ms) is not int
        or not 1 <= window_ms <= 86400000
    ):
        raise ValueError("invalid_metric_selection")
    selector = (
        '{service_name="ecs-ec",environment="'
        + environment
        + '",operation="'
        + operation
        + '"}'
    )
    stream_selector = selector
    if boot_id is not None:
        selector += " |= " + json.dumps('"boot_id":"' + str(UUID(boot_id)) + '"')
    window = f"{window_ms}ms"
    logical = ' | json terminal="event" | (terminal="operation.completed" and operation!="report.generate") or terminal="reception.completed" or terminal="report.completed" or terminal="notification.operation.completed"'
    event = (
        "execution.completed"
        if name.startswith("execution_") or name == "attempt_executions_total"
        else "report.admitted"
        if name == "report_generations_admitted"
        else CATALOG[name][1]
        if name in {"notification_attempts_observed","notification_scheduler_cycles"}
        else None
    )
    pipeline = (
        (' | json terminal="event" | terminal="' + event + '"') if event else logical
    )

    def count(outcome=None):
        """Count a terminal with the same operation/window and only bounded final dimensions."""
        selected = (
            selector
            if outcome is None
            else stream_selector[:-1]
            + ',outcome="'
            + outcome
            + '"}'
            + selector[len(stream_selector) :]
        )
        return (
            "sum by (environment,operation) (count_over_time("
            + selected
            + pipeline
            + ' | __error__="" ['
            + window
            + "]))"
        )

    if name in {
        "operations_total",
        "notification_attempts_observed",
        "notification_scheduler_cycles",
        "attempt_executions_total",
        "report_generations_admitted",
    }:
        return count()
    if name.endswith("error_percent"):
        denominator = count()
        return (
            "100 * (("
            + count("unexpected_error")
            + " or ("
            + denominator
            + " * 0)) / ("
            + denominator
            + " > 0))"
        )
    if name.startswith(("records_", "files_")):
        terminal = (
            "reception.completed"
            if name.startswith("records_")
            else "operation.completed"
        )
        parsed = (
            selector
            + ' | json terminal="event", value="counts.'
            + name
            + '" | terminal="'
            + terminal
            + '" | value!=""'
        )
        return (
            "sum by (environment,operation) (sum_over_time("
            + parsed
            + ' | unwrap value | __error__="" ['
            + window
            + "]))"
        )
    parsed = selector + logical + ' | json duration="duration_ms" | duration!=""'
    if name == "processing_duration_mean_ms":
        return (
            "sum by (environment,operation) (sum_over_time("
            + parsed
            + ' | unwrap duration | __error__="" ['
            + window
            + "])) / sum by (environment,operation) (count_over_time("
            + parsed
            + ' | __error__="" ['
            + window
            + "]))"
        )
    return (
        "quantile_over_time("
        + ("0.5" if name == "processing_duration_p50_ms" else "0.95")
        + ", "
        + parsed
        + ' | unwrap duration | __error__="" ['
        + window
        + "]) by (environment,operation)"
    )
