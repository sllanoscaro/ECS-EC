"""Immutable per-content functional captures; technical logs never establish history coverage."""

from sqlalchemy import select

from ecs_ec.audit.models import CoverageRecord, FunctionalEvent
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.catalog import required_permissions
from ecs_ec.notifications.schemas import validate


def summary_status(items):
    """Only completely known history can claim no news or an unqualified available total."""
    if not items or any(
        item["coverage"] != "completa" or item["count"] is None for item in items
    ):
        return "informacion_insuficiente"
    return "disponible" if any(item["count"] for item in items) else "sin_novedades"


def window(value):
    """Copy a provider's aware endpoints into the closed HTTP/content representation."""
    return {key: stamp(value[key]) for key in ("start", "end")}


async def read_summary(service, uow, version, start, end, cutoff):
    """Read every selected type in the caller's consistent PostgreSQL capture.

    002 owns reception completeness since building registration. Other contents use
    explicit functional coverage evidence when available; absence of a completeness
    proof is unknown even when observed functional events can be counted. Storage
    errors propagate and roll back the entire capture instead of fabricating zero.
    """
    items = []
    for kind in version.content_types:
        item = dict(
            kind=kind,
            count=None,
            coverage="desconocida",
            source_refs=[],
            covered_periods=[],
            known_gaps=[],
            limitation_code="integridad_no_demostrada",
        )
        proof = await uow.session.scalar(
            select(CoverageRecord)
            .where(
                CoverageRecord.content_type == kind,
                CoverageRecord.window_start == start,
                CoverageRecord.window_end == end,
                CoverageRecord.cutoff_at == cutoff,
                CoverageRecord.created_at <= cutoff,
            )
            .order_by(CoverageRecord.created_at.desc())
            .limit(1)
        )
        if start == end:
            item["limitation_code"] = "ventana_inicial_vacia"
        elif proof:
            item.update(
                count=proof.observed_count,
                coverage=proof.integrity,
                covered_periods=proof.covered_periods,
                known_gaps=proof.known_gaps,
                limitation_code=proof.limitation_code,
                source_refs=[
                    dict(
                        module="audit",
                        entity_id=str(proof.id),
                        revision=proof.source_revision or "1",
                    )
                ],
            )
        elif kind in {"recepcion", "calidad"}:
            results = await service.consumption.read_functional_summary(
                ["reception.completed"],
                start,
                end,
                cutoff_at=cutoff,
                permissions=required_permissions(version.config),
                unit_of_work=uow,
            )
            result = results[0]
            refs = list(
                await uow.session.scalars(
                    select(FunctionalEvent).where(
                        FunctionalEvent.id.in_(result["source_refs"])
                    )
                )
            )
            item.update(
                count=result["count"]
                if kind == "recepcion"
                else sum(r.safe_payload["rejected_count"] for r in refs),
                coverage=result["integrity"],
                covered_periods=[window(p) for p in result["covered_periods"]],
                known_gaps=[window(p) for p in result["known_gaps"]],
                limitation_code=result["limitation_code"],
                source_refs=[
                    dict(
                        module=r.source_module,
                        entity_id=str(r.source_entity_id),
                        revision=str(r.source_revision),
                    )
                    for r in refs
                ],
            )
        else:
            event_types = ["administration.changed"]
            rows = list(
                await uow.session.scalars(
                    select(FunctionalEvent)
                    .where(
                        FunctionalEvent.event_type.in_(event_types),
                        FunctionalEvent.occurred_at >= start,
                        FunctionalEvent.occurred_at < end,
                        FunctionalEvent.recorded_at <= cutoff,
                    )
                    .order_by(FunctionalEvent.occurred_at, FunctionalEvent.id)
                )
            )
            if rows:
                # Only these observed points are known; they do not establish continuous history.
                item["count"] = len(rows)
                item["covered_periods"] = []
            item["source_refs"] = [
                dict(
                    module=r.source_module,
                    entity_id=str(r.source_entity_id),
                    revision=str(r.source_revision),
                )
                for r in rows
            ]
        items.append(validate("SummaryItem", item))
    return items
