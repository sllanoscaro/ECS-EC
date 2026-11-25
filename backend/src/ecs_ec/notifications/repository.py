"""008 ordered transactional helpers; no network or hidden commit belongs in repository operations."""

from sqlalchemy import select

from ecs_ec.identity.models import Account, Session
from ecs_ec.identity.schemas import Principal
from ecs_ec.notifications.models import (
    Activation,
    Delivery,
    Episode,
    Message,
    Occurrence,
    Recipient,
    Rule,
    RuleVersion,
)


class NotificationProblem(Exception):
    """Fixed functional reason/status only; never attach raw SQL, SMTP bodies or request inputs."""

    def __init__(self, code, status=422, field_errors=None):
        """Store approved response metadata without stringifying internal errors."""
        self.code, self.status, self.field_errors = code, status, field_errors or []
        super().__init__(code)


async def lock_rule(session, rule_id):
    """Lock the mutable rule before any accounts/deliveries; absent references reveal no metadata."""
    row = await session.scalar(
        select(Rule)
        .where(Rule.id == rule_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise NotificationProblem("not_found", 404)
    return row


async def lock_accounts(session, identifiers):
    """Acquire registered accounts by UUID, reading current fields after concurrent identity mutation."""
    return {
        row.id: row
        for row in await session.scalars(
            select(Account)
            .where(Account.id.in_(identifiers))
            .order_by(Account.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }


async def current_actor(identity, principal, session, accounts, action):
    """Revalidate the original session after ordered locks, including logout/expiration without auth-version changes."""
    from ecs_ec.identity.errors import IdentityProblem

    actor = accounts.get(principal.account_id)
    original = await session.scalar(
        select(Session)
        .where(Session.id == principal.session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not identity.session_valid(actor, original, identity.clock.now()):
        raise IdentityProblem("session_required", 401)
    current = Principal.from_rows(actor, original, identity.settings.building_id)
    identity.authorize(current, action, current.building_id)
    return current


async def end_activation(session, rule, now, reason, *, service):
    """Pause/version replacement cancels pending work only; begun attempts and effective emails remain immutable."""
    rows = await session.scalars(
        select(Activation)
        .where(Activation.rule_id == rule.id, Activation.ended_at.is_(None))
        .with_for_update()
    )
    ids = []
    for activation in rows:
        activation.ended_at = now
        ids.append(activation.id)
    for episode in await session.scalars(
        select(Episode)
        .where(Episode.activation_id.in_(ids), Episode.status == "abierto")
        .with_for_update()
    ):
        episode.status = "finalizado_por_regla"
        episode.closed_at = now
        from ecs_ec.core.retention import anniversary

        episode.retain_until = max(
            episode.retain_until, anniversary(now, service.identity.timezone)
        )
        from ecs_ec.notifications.models import Evidence

        for identifier in [episode.opening_evidence_id, episode.closing_evidence_id]:
            if identifier:
                evidence = await session.get(Evidence, identifier, with_for_update=True)
                evidence.retain_until = max(evidence.retain_until, episode.retain_until)
    deliveries = await session.scalars(
        select(Delivery)
        .join(Message, Message.id == Delivery.message_id)
        .join(Occurrence, Occurrence.id == Message.occurrence_id)
        .join(RuleVersion, RuleVersion.id == Occurrence.version_id)
        .where(RuleVersion.rule_id == rule.id, Delivery.state == "pendiente")
        .order_by(Delivery.id)
        .with_for_update(of=Delivery)
    )
    for delivery in deliveries:
        delivery.state = "cancelada"
        delivery.cancellation_reason = reason
        from ecs_ec.notifications.retention import protect_delivery

        await protect_delivery(service, session, delivery.id, now)


def cancellation_reason(rule, version, account, activation=None, member=True):
    """Return a fixed functional reason rather than exposing an identity/SMTP exception or address."""
    if rule.current_version_id != version.id:
        return "version_sustituida"
    if rule.status != "activa":
        return "regla_pausada"
    if activation is not None and activation.ended_at is not None:
        return "activacion_finalizada"
    if not member:
        return "destinatario_retirado"
    if account is None or account.status != "active":
        return "cuenta_inactiva"
    if account.must_change_password:
        return "renovacion_requerida"
    return "contenido_no_autorizado"


async def prepare_attempt(service, delivery_id, process_ref):
    """After caller reserves capacity, revalidate rules→account→delivery and commit an attempt before any SMTP.

    Returning None means ineligible/not due/already claimed. A begun attempt owns its
    effective email even if identity mutates later. The caller must not free its capacity
    until its blocking transport invocation actually terminates.
    """
    from uuid import uuid4

    from ecs_ec.core.retention import anniversary
    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.identity.services import recipient_eligible
    from ecs_ec.notifications.models import Attempt

    async with UnitOfWork(service.database.sessions) as uow:
        initial = await uow.session.execute(
            select(Delivery, Occurrence, RuleVersion)
            .join(Message, Message.id == Delivery.message_id)
            .join(Occurrence, Occurrence.id == Message.occurrence_id)
            .join(RuleVersion, RuleVersion.id == Occurrence.version_id)
            .where(Delivery.id == delivery_id)
        )
        found = initial.first()
        if not found:
            return None
        original, occurrence, version = found
        rule = await lock_rule(uow.session, version.rule_id)
        accounts = await lock_accounts(uow.session, [original.account_id])
        delivery = await uow.session.scalar(
            select(Delivery)
            .where(Delivery.id == delivery_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        now = service.clock.now()
        if (
            delivery is None
            or delivery.state != "pendiente"
            or delivery.next_attempt_at > now
            or delivery.attempt_count >= 3
        ):
            return None
        account = accounts.get(delivery.account_id)
        message = await uow.session.get(Message, delivery.message_id)
        activation = await uow.session.get(Activation, occurrence.activation_id)
        membership = await uow.session.get(Recipient, (version.id, delivery.account_id))
        if (
            rule.status != "activa"
            or rule.current_version_id != version.id
            or activation.ended_at is not None
            or membership is None
            or not recipient_eligible(account, message.required_permissions)
        ):
            delivery.state = "cancelada"
            delivery.cancellation_reason = cancellation_reason(
                rule, version, account, activation, membership is not None
            )
            await uow.commit()
            return None
        delivery.attempt_count += 1
        delivery.state = "en_intento"
        attempt = Attempt(
            id=uuid4(),
            delivery_id=delivery.id,
            attempt_number=delivery.attempt_count,
            effective_email=account.email,
            authorized_at=now,
            started_at=now,
            transport_kind=delivery.transport_kind,
            process_ref=process_ref,
            created_at=now,
            retain_until=anniversary(now, service.identity.timezone),
        )
        uow.session.add(attempt)
        delivery.retain_until = max(delivery.retain_until, attempt.retain_until)
        message.retain_until = max(message.retain_until, delivery.retain_until)
        occurrence.retain_until = max(occurrence.retain_until, message.retain_until)
        version.retain_until = max(version.retain_until, occurrence.retain_until)
        from ecs_ec.notifications.retention import protect_delivery

        await protect_delivery(service, uow.session, delivery.id, now)
        await uow.commit()
        return dict(
            attempt_id=attempt.id,
            occurrence_id=occurrence.id,
            parent_delivery_id=delivery.parent_delivery_id,
            delivery_id=delivery.id,
            effective_email=attempt.effective_email,
            smtp_message_id=delivery.smtp_message_id,
            functional_content=message.functional_content,
            started_at=attempt.started_at,
            number=attempt.attempt_number,
        )
