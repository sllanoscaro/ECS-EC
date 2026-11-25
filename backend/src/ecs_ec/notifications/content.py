"""Build closed immutable functional snapshots shared by email and authenticated history."""

from ecs_ec.consumption.catalog_storage import BuildingRow
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.schemas import validate
from ecs_ec.notifications.summaries import read_summary, summary_status


async def periodic_content(service, uow, version, slot, cutoff):
    """Capture a fixed logical window and actual source coverage once, before creating its message."""
    from ecs_ec.notifications.schemas import instant

    start, end = instant(slot["window"]["start"]), instant(slot["window"]["end"])
    building = await uow.session.get(BuildingRow, service.building_id)
    if building is None:
        raise ValueError("building_context_missing")
    items = await read_summary(service, uow, version, start, end, cutoff)
    return validate(
        "FunctionalContent",
        dict(
            building_name=building.name,
            type="resumen_periodico",
            priority="normal",
            rule_id=str(version.rule_id),
            rule_version=version.version_number,
            headline=version.config["name"],
            timezone=version.timezone,
            window=slot["window"],
            recovered_periods=[],
            cutoff_at=stamp(cutoff),
            is_late=cutoff > end,
            data_status=summary_status(items),
            evidence=[],
            summary_items=items,
            protected_paths=["/notificaciones"],
            initial_window_empty=slot.get("initial_window_empty", False),
        ),
    )


async def urgent_content(service, uow, version, episode, evidence, event, now):
    """Capture the actual condition/episode/provenance required by FR010–013/021, shared unchanged by UI and SMTP."""
    from ecs_ec.notifications.schemas import instant

    condition = version.config["condition"]
    kind = {
        "consumo": "alerta_consumo",
        "ausencia_datos": "alerta_ausencia",
        "evento_sistema": "alerta_sistema",
    }[condition["kind"]]
    building = await uow.session.get(BuildingRow, service.building_id)
    if building is None:
        raise ValueError("building_context_missing")
    period = (
        evidence["window"] if evidence else event.effective_window if event else None
    )
    paths = (
        ["/consumption/"]
        if evidence
        else ["/costos/"]
        if condition.get("event_type") == "calculo_fallido"
        else ["/reportes/"]
        if condition.get("event_type") == "pdf_fallido"
        else ["/consumption/"]
    )
    reference = (
        dict(
            module=event.source_module,
            entity_id=str(event.source_entity_id),
            revision=str(event.source_revision),
        )
        if event
        else None
    )
    return validate(
        "FunctionalContent",
        dict(
            building_name=building.name,
            type=kind,
            priority="urgente",
            rule_id=str(version.rule_id),
            rule_version=version.version_number,
            headline=version.config["name"],
            timezone=version.timezone,
            window=period,
            recovered_periods=[],
            cutoff_at=stamp(now),
            is_late=bool(period and now > instant(period["end"])),
            data_status="disponible"
            if event or (evidence and evidence["value_kwh"] is not None)
            else "informacion_insuficiente",
            evidence=[evidence] if evidence else [],
            summary_items=[],
            protected_paths=paths,
            episode_id=str(episode.id),
            condition=condition,
            source_event=reference,
            source_event_at=stamp(event.occurred_at) if event else None,
            detected_at=stamp(now),
        ),
    )
