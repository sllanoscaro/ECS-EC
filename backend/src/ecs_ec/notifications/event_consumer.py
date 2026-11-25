"""Consume committed009 events from real002/004/005 producers; SMTP/telemetry never produce recursive alerts."""

from sqlalchemy import exists, select

from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.core.retention import anniversary
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.models import ConsumedEvent
from ecs_ec.notifications.schemas import instant

PRODUCERS = {
    "recepcion_rechazada": ("consumption", "reception.completed"),
    "calculo_fallido": ("costs", "cost.failed"),
    "pdf_fallido": ("reports", "pdf.failed"),
}


async def pending_events(
    uow,
    activation,
    state,
    event_type,
    cutoff,
    building_id,
    *,
    retention_zone,
    limit=100,
):
    """Read bounded stable source identities; filter occurrence before activation and a foreign building if supplied."""
    module, code = PRODUCERS[event_type]
    query = select(FunctionalEvent).where(
        FunctionalEvent.source_module == module,
        FunctionalEvent.event_type == code,
        FunctionalEvent.occurred_at >= activation.activated_at,
        FunctionalEvent.recorded_at <= cutoff,
        ~exists().where(
            ConsumedEvent.activation_id == activation.id,
            ConsumedEvent.source_event_id == FunctionalEvent.id,
        ),
    )
    rows = list(
        await uow.session.scalars(
            query.order_by(FunctionalEvent.recorded_at, FunctionalEvent.id).limit(limit)
        )
    )
    selected = []
    for row in rows:
        acknowledge(uow, activation, row, cutoff, retention_zone)
        state.event_cursor = stamp(row.recorded_at) + "|" + str(row.id)
        payload = row.safe_payload
        if payload.get("building_id") and str(payload["building_id"]) != str(
            building_id
        ):
            continue
        if event_type == "recepcion_rechazada" and not payload.get("rejected_count", 0):
            continue
        selected.append(row)
    return selected


async def historical_updates(
    uow, activation, state, category, cutoff, *, retention_zone, limit=100
):
    """Retain old/corrected period omissions without replaying one alert per historical window."""
    query = select(FunctionalEvent).where(
        FunctionalEvent.source_module == "consumption",
        FunctionalEvent.event_type == "consumption.accepted",
        FunctionalEvent.safe_payload["category_id"].astext == category,
        FunctionalEvent.recorded_at >= activation.activated_at,
        FunctionalEvent.recorded_at <= cutoff,
        ~exists().where(
            ConsumedEvent.activation_id == activation.id,
            ConsumedEvent.source_event_id == FunctionalEvent.id,
        ),
    )
    rows = list(
        await uow.session.scalars(
            query.order_by(FunctionalEvent.recorded_at, FunctionalEvent.id).limit(limit)
        )
    )
    floor = (
        max(activation.activated_at, state.last_valid_window_end)
        if state.last_valid_window_end
        else activation.activated_at
    )
    selected = []
    for row in rows:
        acknowledge(uow, activation, row, cutoff, retention_zone)
        state.event_cursor = stamp(row.recorded_at) + "|" + str(row.id)
        omitted = [
            p for p in row.safe_payload.get("windows", []) if instant(p["end"]) <= floor
        ]
        if omitted:
            selected.append((row, omitted))
    return selected


def acknowledge(uow, activation, event, cutoff, zone):
    """Acknowledgement and evaluation share a transaction; source history lasts at least as long as its consumer."""
    retain = anniversary(cutoff, zone)
    uow.session.add(
        ConsumedEvent(
            activation_id=activation.id,
            source_event_id=event.id,
            created_at=cutoff,
            retain_until=retain,
        )
    )
    event.retain_until = max(event.retain_until, retain)
