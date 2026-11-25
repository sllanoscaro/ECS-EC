"""Explicit administrative duplicate acknowledgement creates a new linked generation, never rewriting an earlier attempt."""

from uuid import uuid4

from sqlalchemy import func, select

from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.permissions import permissions
from ecs_ec.identity.services import recipient_eligible
from ecs_ec.notifications import models
from ecs_ec.notifications.idempotency import digest, lookup
from ecs_ec.notifications.queries import summary
from ecs_ec.notifications.repository import (
    NotificationProblem,
    current_actor,
    lock_accounts,
    lock_rule,
)
from ecs_ec.notifications.retention import protect_delivery
from ecs_ec.notifications.schemas import validate


async def resend(service, principal, parent_id, body, key):
    """Resolve an authorized confirmed action before mutable eligibility checks for a new action."""
    service.authorize(principal, "notifications.deliveries.resend")
    request = dict(parent_delivery_id=str(parent_id), request=body)
    async with UnitOfWork(service.database.sessions) as uow:
        receipt = await lookup(
            uow.session, principal.account_id, "resend", key, request
        )
        parent = await uow.session.get(models.Delivery, parent_id)
        if parent is None:
            raise NotificationProblem("not_found", 404)
        message = await uow.session.get(models.Message, parent.message_id)
        occurrence = await uow.session.get(models.Occurrence, message.occurrence_id)
        version = await uow.session.get(models.RuleVersion, occurrence.version_id)
        rule = await lock_rule(uow.session, version.rule_id)
        if rule.building_id != service.building_id:
            raise NotificationProblem("not_found", 404)
        accounts = await lock_accounts(
            uow.session, {principal.account_id, parent.account_id}
        )
        current = await current_actor(
            service.identity,
            principal,
            uow.session,
            accounts,
            "notifications.deliveries.resend",
        )
        if not set(message.required_permissions) <= permissions(current):
            raise NotificationProblem("not_found", 404)
        if receipt:
            child = await uow.session.get(models.Delivery, receipt.resource_id)
            decision = await uow.session.scalar(
                select(models.ResendDecision).where(
                    models.ResendDecision.new_delivery_id == child.id
                )
            )
            return await result(
                uow.session, child, message, occurrence, version, decision
            )
        reason = body.get("reason", "").strip()
        if (
            not 1 <= len(reason) <= 500
            or body.get("acknowledge_possible_duplicate") is not True
        ):
            raise NotificationProblem("invalid_decision")
        parent = await uow.session.get(
            models.Delivery, parent_id, with_for_update=True, populate_existing=True
        )
        if parent.state not in {"fallida", "indeterminada"}:
            raise NotificationProblem("delivery_not_resendable", 409)
        if (
            rule.status != "activa"
            or rule.current_version_id != version.id
            or not recipient_eligible(
                accounts.get(parent.account_id), message.required_permissions
            )
        ):
            raise NotificationProblem("rule_or_recipient_not_eligible", 409)
        activation = await uow.session.get(models.Activation, occurrence.activation_id)
        if activation.ended_at is not None:
            raise NotificationProblem("activation_ended", 409)
        now = service.clock.now()
        retain = anniversary(now, service.identity.timezone)
        generation = 1 + (
            await uow.session.scalar(
                select(func.max(models.Delivery.generation)).where(
                    models.Delivery.message_id == message.id,
                    models.Delivery.account_id == parent.account_id,
                )
            )
        )
        identifier, decision_id = uuid4(), uuid4()
        child = models.Delivery(
            id=identifier,
            message_id=message.id,
            account_id=parent.account_id,
            generation=generation,
            state="pendiente",
            next_attempt_at=now,
            attempt_count=0,
            smtp_message_id=f"<{identifier}@{service.settings.mail_from.rsplit('@', 1)[1]}>",
            transport_kind=service.settings.mail_transport,
            parent_delivery_id=parent_id,
            created_at=now,
            retain_until=retain,
        )
        decision = models.ResendDecision(
            id=decision_id,
            parent_delivery_id=parent_id,
            new_delivery_id=identifier,
            administrator_id=current.account_id,
            decided_at=now,
            reason=reason,
            acknowledge_possible_duplicate=True,
            idempotency_key=key,
            request_hash=digest(request),
            created_at=now,
            retain_until=retain,
        )
        uow.session.add_all(
            [
                child,
                decision,
                models.Idempotency(
                    actor_id=current.account_id,
                    operation="resend",
                    idempotency_key=key,
                    request_hash=digest(request),
                    resource_id=identifier,
                    http_status=201,
                    resource_revision=generation,
                    resource_metadata={},
                    created_at=now,
                    retain_until=retain,
                ),
            ]
        )
        await protect_delivery(service, uow.session, identifier, now)
        await service.audit.changed(
            uow, current.account_id, rule, "resent", operation_id=decision_id
        )
        response = await result(
            uow.session, child, message, occurrence, version, decision
        )
        await uow.commit()
    if service.wake:
        service.wake.set()
    return response


async def result(session, delivery, message, occurrence, version, decision):
    """Return the existing decision/new delivery identity; no arbitrary request response or personal explanation is cached."""
    return validate(
        "ResendResult",
        dict(
            decision_id=str(decision.id),
            parent_delivery_id=str(decision.parent_delivery_id),
            delivery=await summary(session, delivery, message, occurrence, version),
            possible_duplicate=True,
        ),
    )
