"""Clock-driven silence uses actual acceptance of new data, including the owner's calculated total availability."""

from datetime import timedelta

from ecs_ec.notifications.calendar import stamp


def observe(condition, source, activation, now):
    """Reject an unconfigured source; duplicates/rejections cannot replace source.last_new_data_at."""
    last = source["last_new_data_at"]
    baseline = max(activation.activated_at, last) if last else activation.activated_at
    result = (
        "no_evaluable"
        if source["source_mode"] == "unavailable"
        else "cumple"
        if now - baseline >= timedelta(minutes=condition["silence_minutes"])
        else "no_cumple"
    )
    key = (
        "absence:"
        + str(condition["category_id"])
        + ":"
        + str(source["configuration_revision"])
        + ":"
        + (stamp(last) if last else "initial")
        + ":"
        + result
    )
    return result, key, baseline
