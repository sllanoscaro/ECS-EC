"""PostgreSQL session leadership and bounded, atomically materialized periodic slots."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text

from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import next_occurrences
from ecs_ec.notifications.catalog import required_permissions
from ecs_ec.notifications.content import periodic_content
from ecs_ec.notifications.idempotency import digest
from ecs_ec.notifications.repository import lock_rule
from ecs_ec.notifications.schemas import instant
from ecs_ec.observability.notifications import observe

LEADER_KEY = 800800008


class LeadershipLost(RuntimeError):
    """The dedicated lock-holding connection cannot prove this process still leads."""


class Scheduler:
    """Hold a dedicated session lock; ordinary pooled business sessions never own leadership."""

    def __init__(self, service):
        """Construct without acquiring connections or enabling work."""
        self.service = service
        self.connection = None
        self.pid = None
        self.reconciled = False

    async def acquire(self):
        """Try once; a peer leader is normal and does not affect application readiness."""
        if self.connection is not None:
            return True
        connection = await self.service.database.engine.connect()
        try:
            locked = await connection.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": LEADER_KEY}
            )
            if not locked:
                await connection.close()
                return False
            self.pid = await connection.scalar(text("SELECT pg_backend_pid()"))
            await connection.commit()
            self.connection = connection
            from ecs_ec.notifications.calendar_reconciliation import reconcile

            await reconcile(self)
            self.reconciled = True
            return True
        except BaseException:
            if self.connection is None:
                await connection.close()
            else:
                await self.close()
            raise

    async def check_leadership(self):
        """Never silently reconnect to replace a lost session; a different PID cannot retain its lock."""
        if self.connection is None or self.connection.invalidated:
            raise LeadershipLost()
        try:
            pid = await self.connection.scalar(
                text(
                    "SELECT pg_backend_pid() WHERE EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND pid=pg_backend_pid() AND classid=0 AND objid=:key AND objsubid=1 AND granted)"
                ),
                {"key": LEADER_KEY},
            )
            await self.connection.commit()
        except Exception:
            raise LeadershipLost() from None
        if pid != self.pid:
            raise LeadershipLost()

    async def close(self):
        """Release on its owning connection before returning it to the pool, including partial startup."""
        connection, self.connection = self.connection, None
        self.reconciled = False
        if connection is None:
            return
        try:
            if not connection.invalidated:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": LEADER_KEY}
                )
                await connection.commit()
        finally:
            await connection.close()

    @observe("notification.plan", "notification.scheduler.tick")
    async def tick(self, limit=100):
        """Materialize at most100 due slots per tick and advance each activation in the same commit."""
        if not self.reconciled:
            raise LeadershipLost()
        await self.check_leadership()
        made = 0
        while made < limit:
            async with UnitOfWork(self.service.database.sessions) as uow:
                await uow.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                now = self.service.clock.now()
                row = (
                    await uow.session.execute(
                        select(models.Activation.id, models.Activation.rule_id)
                        .where(
                            models.Activation.ended_at.is_(None),
                            models.Activation.next_due_at <= now,
                        )
                        .order_by(models.Activation.next_due_at, models.Activation.id)
                        .limit(1)
                    )
                ).first()
                if row is None:
                    break
                rule = await lock_rule(uow.session, row.rule_id)
                activation = await uow.session.get(
                    models.Activation, row.id, with_for_update=True
                )
                if (
                    activation.ended_at
                    or rule.status != "activa"
                    or activation.next_due_at > now
                ):
                    continue
                version = await uow.session.get(
                    models.RuleVersion, activation.version_id
                )
                # The stored due instant is authoritative across tzdata reconciliation.
                due = activation.next_due_at
                slot = (
                    activation.next_slot
                    or next_occurrences(
                        version.config["schedule"],
                        version.timezone,
                        due - timedelta(microseconds=1),
                        1,
                    )[0]
                )
                if instant(slot["resolved_at"]) != due:
                    raise ValueError("stored_calendar_slot_mismatch")
                logical = str(activation.id) + ":" + due.isoformat()
                existing = await uow.session.scalar(
                    select(models.Occurrence.id).where(
                        models.Occurrence.version_id == version.id,
                        models.Occurrence.logical_key == logical,
                    )
                )
                if not existing:
                    content = await periodic_content(
                        self.service, uow, version, slot, now
                    )
                    retain = anniversary(now, self.service.identity.timezone)
                    occurrence = models.Occurrence(
                        id=uuid4(),
                        version_id=version.id,
                        activation_id=activation.id,
                        kind="periodica",
                        logical_key=logical,
                        nominal_local_slot=slot["nominal_local"],
                        scheduled_at=due,
                        window_start=instant(slot["window"]["start"]),
                        window_end=due,
                        cutoff_at=now,
                        tzdata_version=activation.tzdata_version,
                        is_late=now > due,
                        initial_window_empty=slot["initial_window_empty"],
                        created_at=now,
                        retain_until=retain,
                    )
                    message = models.Message(
                        id=uuid4(),
                        occurrence_id=occurrence.id,
                        functional_content=content,
                        content_hash=digest(content),
                        required_permissions=list(required_permissions(version.config)),
                        created_at=now,
                        retain_until=retain,
                    )
                    uow.session.add_all([occurrence, message])
                    for raw in version.config["recipient_ids"]:
                        identifier = uuid4()
                        uow.session.add(
                            models.Delivery(
                                id=identifier,
                                message_id=message.id,
                                account_id=UUID(raw),
                                next_attempt_at=now,
                                smtp_message_id=f"<{identifier}@{self.service.settings.mail_from.rsplit('@', 1)[1]}>",
                                transport_kind=self.service.settings.mail_transport,
                                created_at=now,
                                retain_until=retain,
                            )
                        )
                    version.retain_until = max(version.retain_until, retain)
                activation.next_slot = next_occurrences(
                    version.config["schedule"], version.timezone, due, 1
                )[0]
                activation.next_due_at = instant(activation.next_slot["resolved_at"])
                activation.last_materialized_slot = logical
                activation.revision += 1
                await self.check_leadership()
                await uow.commit()
                made += 1
        return made
