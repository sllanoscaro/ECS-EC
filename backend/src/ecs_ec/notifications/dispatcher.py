"""Capacity-before-claim delivery with dedicated SMTP threads and durable evidence-based outcomes."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, text

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.notifications import models
from ecs_ec.notifications.repository import prepare_attempt
from ecs_ec.notifications.templates import render
from ecs_ec.notifications.transports import SMTPTransport, TransportResult
from ecs_ec.observability.notifications import begin_attempt, complete_attempt, observe


def process_key(identifier):
    """A deterministic signed advisory key identifies a live dispatcher's dedicated session."""
    return int.from_bytes(identifier.bytes[:8], "big", signed=True)


class Dispatcher:
    """At most four in-flight threads; each reserved slot owns its call until it actually returns."""

    def __init__(self, service, *, transport=None):
        """Initialize a dedicated executor without opening sockets or claiming durable work."""
        self.service = service
        self.transport = transport or SMTPTransport(service.settings)
        self.process_ref = uuid4()
        self.connection = None
        self.slots = asyncio.Semaphore(service.settings.notification_slots)
        self.executor = ThreadPoolExecutor(
            max_workers=service.settings.notification_slots,
            thread_name_prefix="ecs008-smtp",
        )
        self.selection = asyncio.Lock()
        self.claim_lock = asyncio.Lock()
        self.urgent_turn = 0
        self.active = set()
        self.closed = False
        self.unrecorded = {}

    async def start(self):
        """Advertise liveness before any durable attempt, so a peer restart cannot reconcile active calls."""
        if self.connection is not None and self.connection.invalidated:
            raise RuntimeError("notification_dispatch_liveness_lost")
        if self.connection is None:
            self.connection = await self.service.database.engine.connect()
            await self.connection.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": process_key(self.process_ref)},
            )
            await self.connection.commit()

    async def select_due(self):
        """Use three urgent turns then one periodic whenever both queues contain due work."""
        async with self.selection:
            now = self.service.clock.now()
            async with self.service.database.sessions() as session:
                query = (
                    select(models.Delivery.id)
                    .join(
                        models.Message, models.Message.id == models.Delivery.message_id
                    )
                    .join(
                        models.Occurrence,
                        models.Occurrence.id == models.Message.occurrence_id,
                    )
                    .where(
                        models.Delivery.state == "pendiente",
                        models.Delivery.next_attempt_at <= now,
                        models.Delivery.attempt_count < 3,
                    )
                    .order_by(models.Delivery.next_attempt_at, models.Delivery.id)
                    .limit(1)
                )
                urgent = await session.scalar(
                    query.where(models.Occurrence.kind == "urgente")
                )
                periodic = await session.scalar(
                    query.where(models.Occurrence.kind != "urgente")
                )
                if urgent and periodic:
                    choice = urgent if self.urgent_turn < 3 else periodic
                    self.urgent_turn = (self.urgent_turn + 1) % 4
                    return choice
                return urgent or periodic

    async def finish(self, claim, result):
        """One final result per begun attempt; confirmed transient waits start at its actual completion."""
        async with UnitOfWork(self.service.database.sessions) as uow:
            from ecs_ec.notifications.repository import lock_rule

            rule_id = await uow.session.scalar(
                select(models.RuleVersion.rule_id)
                .join(
                    models.Occurrence,
                    models.Occurrence.version_id == models.RuleVersion.id,
                )
                .join(
                    models.Message, models.Message.occurrence_id == models.Occurrence.id
                )
                .join(models.Delivery, models.Delivery.message_id == models.Message.id)
                .where(models.Delivery.id == claim["delivery_id"])
            )
            await lock_rule(uow.session, rule_id)
            delivery = await uow.session.get(
                models.Delivery, claim["delivery_id"], with_for_update=True
            )
            attempt = await uow.session.get(
                models.Attempt, claim["attempt_id"], with_for_update=True
            )
            if attempt.outcome is not None:
                return
            now = self.service.clock.now()
            attempt.finished_at = now
            attempt.outcome = result.outcome
            attempt.functional_reason_code = result.reason
            if result.outcome == "aceptada":
                attempt.acceptance_confirmed_at = now
                delivery.state = "aceptada"
            elif (
                result.outcome == "no_aceptada_transitoria"
                and delivery.attempt_count < 3
            ):
                delivery.state = "pendiente"
                delivery.next_attempt_at = now + timedelta(
                    minutes=1 if delivery.attempt_count == 1 else 5
                )
            else:
                delivery.state = (
                    "indeterminada" if result.outcome == "indeterminada" else "fallida"
                )
            from ecs_ec.core.retention import anniversary
            from ecs_ec.notifications.retention import protect_delivery

            attempt.retain_until = max(
                attempt.retain_until, anniversary(now, self.service.identity.timezone)
            )
            await protect_delivery(self.service, uow.session, delivery.id, now)
            await uow.commit()

    async def one(self):
        """Reserve before selection/claim; committed attempt is visible before synchronous transport starts."""
        async with self.slots:
            if self.closed:
                return 0
            async with self.claim_lock:
                if self.closed:
                    return 0
                identifier = await self.select_due()
                if identifier is None:
                    return 0
                claim = await prepare_attempt(
                    self.service, identifier, self.process_ref
                )
                if claim is None:
                    return 0
            try:
                handle = begin_attempt(self.service, claim)
                bodies = render(
                    claim["functional_content"],
                    self.service.settings,
                    claim["delivery_id"],
                )
            except ValueError:
                complete_attempt(
                    self.service,
                    handle,
                    TransportResult("no_aceptada_definitiva", "contenido_no_valido"),
                )
                await self.finish(
                    claim,
                    TransportResult("no_aceptada_definitiva", "contenido_no_valido"),
                )
                return 1
            future = asyncio.get_running_loop().run_in_executor(
                self.executor,
                self.transport.send,
                claim["effective_email"],
                claim["smtp_message_id"],
                bodies,
            )
            try:
                result = await asyncio.shield(future)
            except asyncio.CancelledError:
                # Cancellation never releases capacity while the socket-owning thread is active.
                try:
                    result = await asyncio.shield(future)
                except Exception:
                    result = TransportResult(
                        "indeterminada", "confirmacion_no_disponible"
                    )
                complete_attempt(self.service, handle, result)
                await self.finish(claim, result)
                raise
            except Exception:
                result = TransportResult("indeterminada", "confirmacion_no_disponible")
            complete_attempt(self.service, handle, result)
            self.unrecorded[claim["attempt_id"]] = (claim, result)
            await self.finish(claim, result)
            self.unrecorded.pop(claim["attempt_id"], None)
            return 1

    @observe("notification.dispatch")
    async def dispatch_once(self):
        """Drain one wave of available capacity; avoid reserving a slot for future deliveries."""
        if self.closed:
            return 0
        await self.start()
        # Retry only the database result while this process retains unequivocal
        # acceptance evidence. The bounded map never causes another SMTP call.
        for identifier, (claim, result) in list(self.unrecorded.items()):
            await self.finish(claim, result)
            self.unrecorded.pop(identifier, None)
        tasks = [
            asyncio.create_task(self.one())
            for _ in range(self.service.settings.notification_slots)
        ]
        self.active.update(tasks)
        for task in tasks:
            task.add_done_callback(self.active.discard)
        results = await asyncio.gather(*tasks)
        return sum(results)

    async def close(self):
        """Join socket-owning calls before releasing liveness or shutting down the executor."""
        self.closed = True
        if self.active:
            await asyncio.gather(*self.active, return_exceptions=True)
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=False)
        if self.connection:
            try:
                if not self.connection.invalidated:
                    await self.connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": process_key(self.process_ref)},
                    )
                    await self.connection.commit()
            finally:
                await self.connection.close()
                self.connection = None
