"""Reconcile abandoned attempts conservatively and consolidate only untouched periodic deliveries."""

from collections import defaultdict
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select, text

from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.services import recipient_eligible
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.dispatcher import process_key
from ecs_ec.notifications.idempotency import digest
from ecs_ec.notifications.repository import lock_accounts, lock_rule
from ecs_ec.notifications.schemas import validate
from ecs_ec.notifications.summaries import summary_status


async def reconcile_attempts(service):
    """Only a process without its live session lock may have open attempts declared indeterminate."""
    async with service.database.sessions() as session:
        processes = list(
            await session.scalars(
                select(models.Attempt.process_ref)
                .where(models.Attempt.finished_at.is_(None))
                .distinct()
            )
        )
    reconciled = 0
    for process in processes:
        async with UnitOfWork(service.database.sessions) as uow:
            abandoned = await uow.session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": process_key(process)},
            )
            if not abandoned:
                continue
            ids = list(
                await uow.session.scalars(
                    select(models.Attempt.delivery_id)
                    .where(
                        models.Attempt.process_ref == process,
                        models.Attempt.finished_at.is_(None),
                    )
                    .order_by(models.Attempt.delivery_id)
                )
            )
        for identifier in ids:
            reconciled += await reconcile_one(service, identifier, process)
    return reconciled


async def reconcile_one(service, identifier, process):
    """Lock the rule before a delivery; a recorded abandoned outcome and its protected parents commit together."""
    from ecs_ec.notifications.retention import protect_delivery

    async with UnitOfWork(service.database.sessions) as uow:
        rule_id = await uow.session.scalar(
            select(models.RuleVersion.rule_id)
            .join(
                models.Occurrence, models.Occurrence.version_id == models.RuleVersion.id
            )
            .join(models.Message, models.Message.occurrence_id == models.Occurrence.id)
            .join(models.Delivery, models.Delivery.message_id == models.Message.id)
            .where(models.Delivery.id == identifier)
        )
        if rule_id is None:
            return 0
        await lock_rule(uow.session, rule_id)
        delivery = await uow.session.get(
            models.Delivery, identifier, with_for_update=True
        )
        attempt = await uow.session.scalar(
            select(models.Attempt)
            .where(
                models.Attempt.delivery_id == identifier,
                models.Attempt.process_ref == process,
                models.Attempt.finished_at.is_(None),
            )
            .with_for_update()
        )
        if attempt is None:
            return 0
        now = service.clock.now()
        attempt.finished_at = now
        attempt.outcome = "indeterminada"
        attempt.functional_reason_code = "proceso_interrumpido_sin_confirmacion"
        attempt.retain_until = max(
            attempt.retain_until, anniversary(now, service.identity.timezone)
        )
        delivery.state = "indeterminada"
        await protect_delivery(service, uow.session, identifier, now)
        await uow.commit()
        return 1


def recovery_content(contents, now):
    """Aggregate captured members without spanning an already attempted/missing period as covered history."""
    result = deepcopy(contents[0])
    result.pop("initial_window_empty", None)
    result.update(type="resumen_recuperacion", cutoff_at=stamp(now), is_late=True)
    periods = sorted(
        [
            c["window"]
            for c in contents
            if c["window"] and c["window"]["start"] < c["window"]["end"]
        ],
        key=lambda p: p["start"],
    )
    result["recovered_periods"] = periods
    result["window"] = (
        dict(start=periods[0]["start"], end=periods[-1]["end"]) if periods else None
    )
    gaps = [
        dict(start=previous["end"], end=current["start"])
        for previous, current in zip(periods, periods[1:])
        if previous["end"] < current["start"]
    ]
    for item in result["summary_items"]:
        matching = [
            next(i for i in c["summary_items"] if i["kind"] == item["kind"])
            for c in contents
        ]
        item["count"] = (
            sum(i["count"] for i in matching)
            if all(i["count"] is not None for i in matching)
            else None
        )
        item["covered_periods"] = [p for i in matching for p in i["covered_periods"]]
        item["known_gaps"] = [p for i in matching for p in i["known_gaps"]] + gaps
        item["source_refs"] = list(
            {
                (r["module"], r["entity_id"], r["revision"]): r
                for i in matching
                for r in i["source_refs"]
            }.values()
        )
        if any(i["coverage"] == "desconocida" for i in matching):
            item.update(
                coverage="desconocida",
                limitation_code="recuperacion_con_historia_limitada",
            )
        elif gaps or any(i["coverage"] == "incompleta" for i in matching):
            item.update(
                coverage="incompleta", limitation_code="recuperacion_con_huecos"
            )
        else:
            item.update(coverage="completa", limitation_code=None)
    result["data_status"] = summary_status(result["summary_items"])
    return validate("FunctionalContent", result)


async def consolidate(service):
    """Group at least two due original periodic deliveries by version/account, under the shared lock order."""
    query = (
        select(models.Delivery, models.Message, models.Occurrence, models.RuleVersion)
        .join(models.Message, models.Message.id == models.Delivery.message_id)
        .join(models.Occurrence, models.Occurrence.id == models.Message.occurrence_id)
        .join(models.RuleVersion, models.RuleVersion.id == models.Occurrence.version_id)
        .where(
            models.Delivery.state == "pendiente",
            models.Delivery.attempt_count == 0,
            models.Delivery.generation == 0,
            models.Occurrence.kind == "periodica",
            models.Occurrence.scheduled_at < service.clock.now(),
        )
    )
    async with service.database.sessions() as session:
        initial = list(await session.execute(query))
    groups = defaultdict(list)
    for delivery, message, occurrence, version in initial:
        groups[(version.rule_id, version.id, delivery.account_id)].append(delivery.id)
    made = 0
    for (rule_id, version_id, account_id), identifiers in sorted(groups.items()):
        if len(identifiers) < 2:
            continue
        async with UnitOfWork(service.database.sessions) as uow:
            rule = await lock_rule(uow.session, rule_id)
            accounts = await lock_accounts(uow.session, [account_id])
            rows = list(
                await uow.session.execute(
                    query.where(models.Delivery.id.in_(identifiers))
                    .order_by(models.Occurrence.scheduled_at, models.Delivery.id)
                    .with_for_update(of=models.Delivery)
                )
            )
            if (
                len(rows) < 2
                or rule.status != "activa"
                or rule.current_version_id != version_id
            ):
                continue
            if not recipient_eligible(
                accounts.get(account_id), rows[0][1].required_permissions
            ):
                continue
            now = service.clock.now()
            retain = anniversary(now, service.identity.timezone)
            content = recovery_content([row[1].functional_content for row in rows], now)
            oid, mid, did = uuid4(), uuid4(), uuid4()
            occurrence = models.Occurrence(
                id=oid,
                version_id=version_id,
                activation_id=rows[-1][2].activation_id,
                kind="recuperacion",
                logical_key="recovery:"
                + digest(sorted(str(row[0].id) for row in rows)),
                cutoff_at=now,
                scheduled_at=rows[-1][2].scheduled_at,
                tzdata_version=rows[-1][2].tzdata_version,
                is_late=True,
                created_at=now,
                retain_until=retain,
            )
            message = models.Message(
                id=mid,
                occurrence_id=oid,
                functional_content=content,
                content_hash=digest(content),
                required_permissions=rows[0][1].required_permissions,
                created_at=now,
                retain_until=retain,
            )
            delivery = models.Delivery(
                id=did,
                message_id=mid,
                account_id=account_id,
                next_attempt_at=now,
                smtp_message_id=f"<{did}@{service.settings.mail_from.rsplit('@', 1)[1]}>",
                transport_kind=service.settings.mail_transport,
                created_at=now,
                retain_until=retain,
            )
            uow.session.add_all([occurrence, message, delivery])
            for original, old_message, old_occurrence, version in rows:
                original.state = "cancelada"
                original.cancellation_reason = "consolidada_en_recuperacion"
                original.retain_until = max(original.retain_until, retain)
                old_message.retain_until = max(old_message.retain_until, retain)
                old_occurrence.retain_until = max(old_occurrence.retain_until, retain)
                version.retain_until = max(version.retain_until, retain)
                uow.session.add(
                    models.RecoveryMember(
                        original_delivery_id=original.id,
                        recovery_delivery_id=did,
                        original_slot=old_occurrence.logical_key,
                        original_window=old_message.functional_content["window"],
                        created_at=now,
                    )
                )
            await uow.commit()
            made += 1
    return made
