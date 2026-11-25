"""008 rule orchestration: live006 grants, ordered locks, immutable versions and atomic009 evidence.

This service never sends email. Configured API actions can be used while SMTP is down;
activation admits future work only after preview and current account checks.
"""

from uuid import UUID, uuid4

from sqlalchemy import select, tuple_

from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.models import Account
from ecs_ec.identity.pagination import decode_cursor, encode_cursor
from ecs_ec.identity.services import recipient_eligible
from ecs_ec.notifications import models, preview
from ecs_ec.notifications.audit import NotificationAudit
from ecs_ec.notifications.calendar import next_occurrences, stamp, tzdata_version
from ecs_ec.notifications.catalog import (
    PERMISSIONS,
    content_types,
)
from ecs_ec.notifications.idempotency import digest, lookup, revision
from ecs_ec.notifications.recipients import eligible_accounts
from ecs_ec.notifications.repository import (
    NotificationProblem,
    current_actor,
    end_activation,
    lock_accounts,
    lock_rule,
)
from ecs_ec.notifications.schemas import instant, validate


class Notifications:
    """Own008 service state and injected providers; the process supervisor is registered separately."""

    def __init__(self, database, clock, identity, consumption, settings):
        """Receive installed owners and explicit mail configuration; no network or startup work."""
        self.database, self.clock, self.identity, self.consumption, self.settings = (
            database,
            clock,
            identity,
            consumption,
            settings,
        )
        self.building_id = identity.settings.building_id
        self.audit = NotificationAudit(clock, identity.timezone)
        self.wake = None
        self.telemetry = None

    def authorize(self, principal, action="notifications.rules.manage"):
        """Use006's fixed action catalog and configured building, never a role declared by the caller."""
        self.identity.authorize(principal, action, self.building_id)

    async def rule_view(self, session, rule, version=None, metadata=None):
        """Project one current or immutable-receipt version; exclude actors, permission tokens and recipient credentials."""
        version = version or await session.get(
            models.RuleVersion, rule.current_version_id
        )
        active = await session.scalar(
            select(models.Activation).where(
                models.Activation.rule_id == rule.id,
                models.Activation.ended_at.is_(None),
            )
        )
        data = dict(
            id=str(rule.id),
            status=rule.status,
            revision=rule.revision,
            current_version_id=str(version.id),
            version_number=version.version_number,
            config=version.config,
            effective_content_types=version.content_types,
            next_due_at=stamp(active.next_due_at)
            if active and active.next_due_at
            else None,
            created_at=stamp(rule.created_at),
            updated_at=stamp(rule.updated_at),
        )
        if metadata:
            data.update(metadata)
        return validate("Rule", data)

    async def get_rule(self, principal, identifier):
        """Read administrative rule metadata only after current management permission."""
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            rule = await uow.session.get(models.Rule, identifier)
            if rule is None or rule.building_id != self.building_id:
                raise NotificationProblem("not_found", 404)
            return await self.rule_view(uow.session, rule)

    async def rules(self, principal, limit=25, cursor=None, status=None):
        """Page stable created_at/UUID order with a signed filter-bound continuation."""
        self.authorize(principal)
        query = select(models.Rule).where(models.Rule.building_id == self.building_id)
        filters = {"status": status}
        if status:
            if status not in {"activa", "pausada", "desactivada"}:
                raise NotificationProblem("invalid_status")
            query = query.where(models.Rule.status == status)
        if cursor:
            last = decode_cursor(
                self.identity.settings, cursor, "notifications.rules", filters
            )
            query = query.where(
                tuple_(models.Rule.created_at, models.Rule.id)
                > tuple_(instant(last["at"]), UUID(last["id"]))
            )
        async with UnitOfWork(self.database.sessions) as uow:
            rows = list(
                await uow.session.scalars(
                    query.order_by(models.Rule.created_at, models.Rule.id).limit(
                        limit + 1
                    )
                )
            )
            token = (
                encode_cursor(
                    self.identity.settings,
                    "notifications.rules",
                    filters,
                    {
                        "at": stamp(rows[limit - 1].created_at),
                        "id": str(rows[limit - 1].id),
                    },
                )
                if len(rows) > limit
                else None
            )
            return dict(
                items=[await self.rule_view(uow.session, row) for row in rows[:limit]],
                next_cursor=token,
            )

    async def recipients(self, principal, limit=25, cursor=None, kinds=None):
        """Expose registered active accounts only to management; annotate full-content eligibility and bounded pagination."""
        self.authorize(principal)
        kinds = kinds or ["recepcion"]
        if any(kind not in PERMISSIONS for kind in kinds):
            raise NotificationProblem("invalid_content")
        required = {PERMISSIONS[kind] for kind in kinds}
        filters = {"contents": sorted(set(kinds))}
        query = select(Account).where(Account.status == "active")
        if cursor:
            last = decode_cursor(
                self.identity.settings, cursor, "notifications.recipients", filters
            )
            query = query.where(
                tuple_(Account.created_at, Account.id)
                > tuple_(instant(last["at"]), UUID(last["id"]))
            )
        async with UnitOfWork(self.database.sessions) as uow:
            rows = list(
                await uow.session.scalars(
                    query.order_by(Account.created_at, Account.id).limit(limit + 1)
                )
            )
            items = [
                dict(
                    id=str(row.id),
                    display_name=row.email,
                    current_email=row.email,
                    role=row.role,
                    eligible=recipient_eligible(row, required),
                    reason_code=None
                    if recipient_eligible(row, required)
                    else "contenido_no_autorizado",
                )
                for row in rows[:limit]
            ]
            token = (
                encode_cursor(
                    self.identity.settings,
                    "notifications.recipients",
                    filters,
                    {
                        "at": stamp(rows[limit - 1].created_at),
                        "id": str(rows[limit - 1].id),
                    },
                )
                if len(rows) > limit
                else None
            )
            return dict(items=items, next_cursor=token)

    async def preview(self, principal, config):
        """Persist only an opaque token digest and validation context, without modifying rules or sending."""
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            accounts = await eligible_accounts(
                uow.session, config, extra=[principal.account_id]
            )
            await current_actor(
                self.identity,
                principal,
                uow.session,
                accounts,
                "notifications.rules.manage",
            )
            result = await preview.create(
                uow.session, principal.account_id, config, accounts, self.clock.now()
            )
            await uow.commit()
            return validate("Preview", result)

    async def versions(self, principal, identifier, limit=25, cursor=None):
        """Return immutable revisions after management permission; never delete or silently overwrite configurations."""
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            rule = await uow.session.get(models.Rule, identifier)
            if rule is None or rule.building_id != self.building_id:
                raise NotificationProblem("not_found", 404)
            filters = {"rule": str(identifier)}
            query = select(models.RuleVersion).where(
                models.RuleVersion.rule_id == identifier
            )
            if cursor:
                last = decode_cursor(
                    self.identity.settings, cursor, "notifications.versions", filters
                )
                query = query.where(models.RuleVersion.version_number > last["version"])
            rows = list(
                await uow.session.scalars(
                    query.order_by(models.RuleVersion.version_number).limit(limit + 1)
                )
            )
            return dict(
                items=[
                    dict(
                        id=str(row.id),
                        rule_id=str(row.rule_id),
                        version_number=row.version_number,
                        config=row.config,
                        created_at=stamp(row.created_at),
                        created_by=str(row.created_by),
                        retired_at=stamp(row.retired_at) if row.retired_at else None,
                    )
                    for row in rows[:limit]
                ],
                next_cursor=encode_cursor(
                    self.identity.settings,
                    "notifications.versions",
                    filters,
                    {"version": rows[limit - 1].version_number},
                )
                if len(rows) > limit
                else None,
            )

    async def mutate(
        self, principal, action, body, key, *, identifier=None, if_match=None
    ):
        """Apply one authorized command; committed idempotency wins before revision/preview expiry checks."""
        self.authorize(principal)
        operation = action + ":" + (str(identifier) if identifier else "new")
        async with UnitOfWork(self.database.sessions) as uow:
            receipt = await lookup(
                uow.session, principal.account_id, operation, key, body
            )
            if receipt:
                version = await uow.session.get(models.RuleVersion, receipt.resource_id)
                rule = await lock_rule(uow.session, version.rule_id)
                if rule.building_id != self.building_id:
                    raise NotificationProblem("not_found", 404)
                accounts = await lock_accounts(uow.session, [principal.account_id])
                await current_actor(
                    self.identity,
                    principal,
                    uow.session,
                    accounts,
                    "notifications.rules.manage",
                )
                return await self.rule_view(
                    uow.session, rule, version, receipt.resource_metadata
                )
            now = self.clock.now()
            created = action == "created"
            if created:
                identifier = uuid4()
                rule = models.Rule(
                    id=identifier,
                    building_id=self.building_id,
                    name=body["name"],
                    current_version_id=uuid4(),
                    status="desactivada",
                    revision=1,
                    created_by=principal.account_id,
                    created_at=now,
                    updated_at=now,
                )
                old_version = None
                uow.session.add(rule)
            else:
                rule = await lock_rule(uow.session, identifier)
                if rule.building_id != self.building_id:
                    raise NotificationProblem("not_found", 404)
                revision(if_match, rule.revision)
                old_version = await uow.session.get(
                    models.RuleVersion, rule.current_version_id
                )
            config = body if action in {"created", "revised"} else old_version.config
            old_ids = (
                list(
                    await uow.session.scalars(
                        select(models.Recipient.account_id).where(
                            models.Recipient.version_id == old_version.id
                        )
                    )
                )
                if old_version
                else []
            )
            if action == "paused":
                accounts = await lock_accounts(
                    uow.session, set(old_ids) | {principal.account_id}
                )
            else:
                accounts = await eligible_accounts(
                    uow.session, config, extra=[principal.account_id, *old_ids]
                )
            await current_actor(
                self.identity,
                principal,
                uow.session,
                accounts,
                "notifications.rules.manage",
            )
            now = self.clock.now()
            if action in {"created", "revised"}:
                if not created:
                    await end_activation(
                        uow.session, rule, now, "version_sustituida", service=self
                    )
                    old_version.retired_at = now
                    old_version.retain_until = max(
                        old_version.retain_until,
                        anniversary(now, self.identity.timezone),
                    )
                    rule.revision += 1
                    rule.status = "pausada"
                version_id = rule.current_version_id if created else uuid4()
                schedule_id = uuid4() if config["mode"] == "periodica" else None
                condition_id = uuid4() if config["mode"] == "urgente" else None
                version = models.RuleVersion(
                    id=version_id,
                    rule_id=rule.id,
                    version_number=1 if created else old_version.version_number + 1,
                    mode=config["mode"],
                    content_types=list(content_types(config)),
                    timezone=config["timezone"],
                    config=config,
                    schedule_id=schedule_id,
                    condition_id=condition_id,
                    created_by=principal.account_id,
                    created_at=now,
                    retain_until=anniversary(now, self.identity.timezone),
                )
                uow.session.add(version)
                if schedule_id:
                    schedule = dict(config["schedule"])
                    schedule["starts_at"] = instant(schedule["starts_at"])
                    uow.session.add(
                        models.Schedule(
                            id=schedule_id,
                            version_id=version_id,
                            timezone=config["timezone"],
                            **schedule,
                        )
                    )
                else:
                    data = dict(config["condition"])
                    window = data.pop("window", None)
                    if window:
                        data.update(
                            window_kind=window["kind"],
                            measurement_interval_seconds=window.get(
                                "measurement_interval_seconds"
                            ),
                        )
                    if "threshold_kwh" in data:
                        from decimal import Decimal

                        data["threshold_kwh"] = Decimal(data["threshold_kwh"])
                    uow.session.add(
                        models.Condition(id=condition_id, version_id=version_id, **data)
                    )
                for raw in config["recipient_ids"]:
                    uow.session.add(
                        models.Recipient(version_id=version_id, account_id=UUID(raw))
                    )
                rule.current_version_id = version_id
                rule.name = config["name"]
                rule.updated_at = now
            elif action == "activated":
                if rule.status == "activa":
                    raise NotificationProblem("already_active", 409)
                await preview.require(
                    uow.session,
                    body.get("preview_token"),
                    principal.account_id,
                    config,
                    accounts,
                    now,
                )
                dates = (
                    next_occurrences(config["schedule"], config["timezone"], now, 1)
                    if config["mode"] == "periodica"
                    else []
                )
                uow.session.add(
                    models.Activation(
                        id=uuid4(),
                        rule_id=rule.id,
                        version_id=rule.current_version_id,
                        activated_at=now,
                        next_due_at=instant(dates[0]["resolved_at"]) if dates else None,
                        next_slot=dates[0] if dates else None,
                        tzdata_version=tzdata_version(),
                        actor_id=principal.account_id,
                    )
                )
                rule.status = "activa"
                rule.revision += 1
                rule.updated_at = now
            elif action == "paused":
                await end_activation(
                    uow.session, rule, now, "regla_pausada", service=self
                )
                rule.status = "pausada"
                rule.revision += 1
                rule.updated_at = now
            else:
                raise NotificationProblem("invalid_action")
            current_version = await uow.session.get(
                models.RuleVersion, rule.current_version_id
            )
            current_version.retain_until = max(
                current_version.retain_until, anniversary(now, self.identity.timezone)
            )
            await uow.session.flush()
            await self.audit.changed(uow, principal.account_id, rule, action)
            result = await self.rule_view(uow.session, rule)
            uow.session.add(
                models.Idempotency(
                    actor_id=principal.account_id,
                    operation=operation,
                    idempotency_key=key,
                    request_hash=digest(body),
                    resource_id=rule.current_version_id,
                    http_status=201 if created else 200,
                    resource_revision=rule.revision,
                    resource_metadata={
                        field: result[field]
                        for field in ["status", "revision", "next_due_at", "updated_at"]
                    },
                    created_at=now,
                    retain_until=anniversary(now, self.identity.timezone),
                )
            )
            from datetime import timedelta

            from ecs_ec.identity.models import Session

            original = await uow.session.get(Session, principal.session_id)
            original.last_activity_at = max(original.last_activity_at, now)
            original.idle_expires_at = min(
                original.absolute_expires_at,
                original.last_activity_at + timedelta(minutes=30),
            )
            await uow.commit()
        if self.wake:
            self.wake.set()
        return result
