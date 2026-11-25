"""Protected notification projections use current grants and signed, filter-bound pagination."""

from uuid import UUID

from sqlalchemy import select, tuple_

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.pagination import decode_cursor, encode_cursor
from ecs_ec.identity.permissions import permissions
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.repository import (
    NotificationProblem,
    current_actor,
    lock_accounts,
)
from ecs_ec.notifications.schemas import instant, validate


async def summary(session, delivery, message, occurrence, version):
    """Project one recipient identity without email directory or other recipients."""
    recovery = await session.get(models.RecoveryMember, delivery.id)
    window = message.functional_content["window"]
    return validate(
        "DeliverySummary",
        dict(
            id=str(delivery.id),
            rule_id=str(version.rule_id),
            rule_name=version.config["name"],
            rule_version=version.version_number,
            account_id=str(delivery.account_id),
            type=message.functional_content["type"],
            state=delivery.state,
            transport_kind=delivery.transport_kind,
            scheduled_at=stamp(occurrence.scheduled_at)
            if occurrence.scheduled_at
            else None,
            detected_at=stamp(occurrence.detected_at)
            if occurrence.detected_at
            else None,
            window=window,
            created_at=stamp(delivery.created_at),
            attempt_count=delivery.attempt_count,
            next_attempt_at=stamp(delivery.next_attempt_at)
            if delivery.state == "pendiente"
            else None,
            parent_delivery_id=str(delivery.parent_delivery_id)
            if delivery.parent_delivery_id
            else None,
            recovery_delivery_id=str(recovery.recovery_delivery_id)
            if recovery
            else None,
            initial_window_empty=message.functional_content.get(
                "initial_window_empty", False
            ),
        ),
    )


def authorized_query(service, principal):
    """Filter unauthorized content before pagination or object existence checks."""
    grants = permissions(principal)
    query = (
        select(models.Delivery, models.Message, models.Occurrence, models.RuleVersion)
        .join(models.Message, models.Message.id == models.Delivery.message_id)
        .join(models.Occurrence, models.Occurrence.id == models.Message.occurrence_id)
        .join(models.RuleVersion, models.RuleVersion.id == models.Occurrence.version_id)
        .join(models.Rule, models.Rule.id == models.RuleVersion.rule_id)
        .where(
            models.Rule.building_id == service.building_id,
            models.Message.required_permissions.contained_by(sorted(grants)),
        )
    )
    if "notifications.rules.manage" not in grants:
        query = query.where(models.Delivery.account_id == principal.account_id)
    return query


async def fresh(service, uow, principal):
    """Revalidate the durable original006 session after reading/locking its current account."""
    accounts = await lock_accounts(uow.session, [principal.account_id])
    return await current_actor(
        service.identity,
        principal,
        uow.session,
        accounts,
        "notifications.deliveries.read",
    )


async def deliveries(
    service,
    principal,
    *,
    limit=25,
    cursor=None,
    start=None,
    end=None,
    state=None,
    rule_id=None,
    recipient_id=None,
):
    """Read newest-first at one cutoff; rejected administrative filters never widen an operator's scope."""
    service.authorize(principal, "notifications.deliveries.read")
    if not 1 <= limit <= 100:
        raise NotificationProblem("invalid_input")
    if (rule_id or recipient_id) and "notifications.rules.manage" not in permissions(
        principal
    ):
        raise NotificationProblem("forbidden", 403)
    try:
        start = instant(start) if start else None
        end = instant(end) if end else None
        if start and end and start >= end:
            raise ValueError()
        if state and state not in {
            "pendiente",
            "en_intento",
            "aceptada",
            "fallida",
            "cancelada",
            "indeterminada",
        }:
            raise ValueError()
    except ValueError, TypeError:
        raise NotificationProblem("invalid_input") from None
    filters = dict(
        start=stamp(start) if start else None,
        end=stamp(end) if end else None,
        state=state,
        rule_id=str(rule_id) if rule_id else None,
        recipient_id=str(recipient_id) if recipient_id else None,
        actor=str(principal.account_id),
    )
    position = (
        decode_cursor(
            service.identity.settings, cursor, "notifications.deliveries", filters
        )
        if cursor
        else None
    )
    cutoff = instant(position["cutoff"]) if position else service.clock.now()
    async with UnitOfWork(service.database.sessions) as uow:
        principal = await fresh(service, uow, principal)
        if (
            rule_id or recipient_id
        ) and "notifications.rules.manage" not in permissions(principal):
            raise NotificationProblem("forbidden", 403)
        query = authorized_query(service, principal).where(
            models.Delivery.created_at <= cutoff
        )
        if start:
            query = query.where(models.Delivery.created_at >= start)
        if end:
            query = query.where(models.Delivery.created_at < end)
        if state:
            query = query.where(models.Delivery.state == state)
        if rule_id:
            query = query.where(models.RuleVersion.rule_id == rule_id)
        if recipient_id:
            query = query.where(models.Delivery.account_id == recipient_id)
        if position:
            query = query.where(
                tuple_(models.Delivery.created_at, models.Delivery.id)
                < tuple_(instant(position["at"]), UUID(position["id"]))
            )
        rows = list(
            await uow.session.execute(
                query.order_by(
                    models.Delivery.created_at.desc(), models.Delivery.id.desc()
                ).limit(limit + 1)
            )
        )
        items = [await summary(uow.session, *row) for row in rows[:limit]]
        token = (
            encode_cursor(
                service.identity.settings,
                "notifications.deliveries",
                filters,
                dict(
                    at=stamp(rows[limit - 1][0].created_at),
                    id=str(rows[limit - 1][0].id),
                    cutoff=stamp(cutoff),
                ),
            )
            if len(rows) > limit
            else None
        )
        return validate("DeliveryPage", dict(items=items, next_cursor=token))


async def delivery_detail(service, principal, identifier):
    """Only the recipient or an administrator with all current content grants sees content and effective attempts."""
    service.authorize(principal, "notifications.deliveries.read")
    async with UnitOfWork(service.database.sessions) as uow:
        principal = await fresh(service, uow, principal)
        row = (
            await uow.session.execute(
                authorized_query(service, principal).where(
                    models.Delivery.id == identifier
                )
            )
        ).first()
        if row is None:
            raise NotificationProblem("not_found", 404)
        delivery, message, occurrence, version = row
        attempts = list(
            await uow.session.scalars(
                select(models.Attempt)
                .where(models.Attempt.delivery_id == identifier)
                .order_by(models.Attempt.attempt_number)
            )
        )
        return validate(
            "DeliveryDetail",
            dict(
                delivery=await summary(uow.session, *row),
                content=message.functional_content,
                attempts=[
                    dict(
                        id=str(a.id),
                        number=a.attempt_number,
                        effective_email=a.effective_email,
                        authorized_at=stamp(a.authorized_at),
                        started_at=stamp(a.started_at),
                        finished_at=stamp(a.finished_at) if a.finished_at else None,
                        outcome=a.outcome,
                        functional_reason_code=a.functional_reason_code,
                        transport_kind=a.transport_kind,
                    )
                    for a in attempts
                ],
                cancellation_reason=delivery.cancellation_reason,
            ),
        )
