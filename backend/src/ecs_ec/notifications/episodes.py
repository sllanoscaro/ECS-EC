"""Atomic evaluation/evidence/cursor/episode/occurrence transitions under each actual rule lock."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from ecs_ec.consumption.calendar import containing_block
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.notifications import models
from ecs_ec.notifications.absence import observe
from ecs_ec.notifications.adapters import ConsumptionAdapter
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.catalog import required_permissions
from ecs_ec.notifications.evaluator import compare_window
from ecs_ec.notifications.event_consumer import historical_updates, pending_events
from ecs_ec.notifications.idempotency import digest
from ecs_ec.notifications.repository import lock_rule
from ecs_ec.notifications.schemas import instant, validate
from ecs_ec.observability.notifications import observe as observe_operation


def source_reference(event):
    """Preserve approved producer identity/revision, never a technical log reference or a raw payload."""
    return dict(
        module=event.source_module,
        entity_id=str(event.source_entity_id),
        revision=str(event.source_revision),
    )


class Evaluator:
    """Clock/event wakeups use current real sources; identical evidence remains one durable evaluation."""

    def __init__(self, service):
        """Bind actual001/002 provider and existing008 service without introducing producer dependencies."""
        self.service = service
        self.source = ConsumptionAdapter(service.consumption)
        self.after = None

    async def tick(self, limit=100):
        """Evaluate at most100 active urgent rules, serializing each independently against pause/revision."""
        async with self.service.database.sessions() as session:
            query = (
                select(models.Rule.id)
                .join(
                    models.RuleVersion,
                    models.RuleVersion.id == models.Rule.current_version_id,
                )
                .where(
                    models.Rule.status == "activa", models.RuleVersion.mode == "urgente"
                )
                .order_by(models.Rule.id)
                .limit(limit)
            )
            ids = list(
                await session.scalars(
                    query.where(models.Rule.id > self.after) if self.after else query
                )
            )
            if not ids and self.after:
                self.after = None
                ids = list(await session.scalars(query))
            if ids:
                self.after = ids[-1]
        made = 0
        for identifier in ids:
            made += await self.rule(identifier)
        return made

    @observe_operation("notification.evaluate")
    async def rule(self, identifier):
        """Retry a whole serialized evaluation after expected PostgreSQL conflicts, never a partial transition."""
        import asyncio
        from hashlib import sha256

        from sqlalchemy.ext.asyncio import async_sessionmaker

        key = int.from_bytes(
            sha256(("notifications008:evaluate:" + str(identifier)).encode()).digest()[
                :8
            ],
            "big",
            signed=True,
        )
        # Acquire before the REPEATABLE READ snapshot, then reuse the same connection.
        # A peer must not keep an old snapshot while waiting for another evaluator.
        async with self.service.database.engine.connect() as connection:
            await connection.execute(
                text("SELECT pg_advisory_lock(:key)"), {"key": key}
            )
            await connection.commit()
            try:
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                for attempt in range(5):
                    try:
                        return await self.evaluate_rule(identifier, sessions)
                    except DBAPIError as error:
                        if (
                            getattr(error.orig, "sqlstate", None)
                            not in {"40001", "40P01"}
                            or attempt == 4
                        ):
                            raise
                        await asyncio.sleep(0)
            finally:
                await connection.rollback()
                if not connection.invalidated:
                    await connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                    )
                    await connection.commit()

    async def evaluate_rule(self, identifier, sessions):
        """State, evidence and any new delivery commit together; no notification on rollback or non-evaluable history."""
        async with UnitOfWork(sessions) as uow:
            await uow.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            )
            rule = await lock_rule(uow.session, identifier)
            if rule.status != "activa":
                return 0
            version = await uow.session.get(models.RuleVersion, rule.current_version_id)
            if version.mode != "urgente":
                return 0
            activation = await uow.session.scalar(
                select(models.Activation)
                .where(
                    models.Activation.rule_id == identifier,
                    models.Activation.ended_at.is_(None),
                )
                .with_for_update()
            )
            if activation is None:
                return 0
            condition = version.config["condition"]
            scope = condition.get("category_id", condition.get("event_type"))
            state = await uow.session.get(
                models.EvaluationState, (activation.id, scope), with_for_update=True
            )
            if state is None:
                state = models.EvaluationState(
                    activation_id=activation.id, scope_key=scope
                )
                uow.session.add(state)
            now = self.service.clock.now()
            made = 0
            if condition["kind"] == "evento_sistema":
                events = await pending_events(
                    uow,
                    activation,
                    state,
                    condition["event_type"],
                    now,
                    self.service.building_id,
                    retention_zone=self.service.identity.timezone,
                )
                for event in events:
                    made += await self.record(
                        uow,
                        version,
                        activation,
                        state,
                        "event:" + str(event.id),
                        "cumple",
                        dict(
                            kind="evento_sistema",
                            source_ref=source_reference(event),
                            occurred_at=stamp(event.occurred_at),
                        ),
                        None,
                        event=event,
                    )
            else:
                source = await self.source.source_status(
                    scope, cutoff_at=now, unit_of_work=uow
                )
                if condition["kind"] == "ausencia_datos":
                    result, key, baseline = observe(condition, source, activation, now)
                    state.last_new_data_accepted_at = source["last_new_data_at"]
                    evidence = (
                        self.absence_evidence(condition, source, baseline, now)
                        if now > baseline
                        else None
                    )
                    payload = evidence or dict(
                        kind="ausencia_datos",
                        result=result,
                        source_mode=source["source_mode"],
                        last_new_data_at=stamp(source["last_new_data_at"])
                        if source["last_new_data_at"]
                        else None,
                    )
                    made += await self.record(
                        uow, version, activation, state, key, result, payload, evidence
                    )
                else:
                    for event, omitted in await historical_updates(
                        uow,
                        activation,
                        state,
                        scope,
                        now,
                        retention_zone=self.service.identity.timezone,
                    ):
                        made += await self.record(
                            uow,
                            version,
                            activation,
                            state,
                            "historical:" + str(event.id),
                            "omitida_historica",
                            dict(
                                kind="omision_historica",
                                source_ref=source_reference(event),
                                omitted_windows=omitted,
                                occurred_at=stamp(event.occurred_at),
                            ),
                            None,
                            event=event,
                        )
                    resolution = condition["window"]["kind"]
                    owner_resolution = {
                        "hora": "hour",
                        "dia": "day",
                        "mes": "month",
                        "anio": "year",
                    }.get(resolution, resolution)
                    # The owner selects whole windows by start. Look back only to the
                    # containing activation window, then reject closed preactivation evidence.
                    lower = (
                        activation.activated_at
                        - timedelta(
                            seconds=condition["window"]["measurement_interval_seconds"]
                        )
                        if resolution == "intervalo"
                        else containing_block(
                            activation.activated_at, owner_resolution, version.timezone
                        ).start
                    )
                    window = await self.source.latest_admissible_window(
                        building_id=self.service.building_id,
                        category_id=scope,
                        resolution=resolution,
                        timezone=version.timezone,
                        activation_at=lower,
                        cursor=state.source_cursor,
                        cutoff_at=now,
                        unit_of_work=uow,
                    )
                    result = compare_window(condition, window)
                    historical = window.period and (
                        window.period.end <= activation.activated_at
                        or (
                            state.last_valid_window_end
                            and (
                                window.period.end < state.last_valid_window_end
                                or (
                                    window.period.end == state.last_valid_window_end
                                    and window.cursor != state.source_cursor
                                )
                            )
                        )
                    )
                    if historical:
                        result = "omitida_historica"
                    key = digest(
                        dict(
                            category=scope,
                            revision=window.evidence_revision,
                            period=window.period.model_dump(mode="json")
                            if window.period
                            else None,
                            source_revision=source["configuration_revision"],
                            result=result,
                        )
                    )
                    evidence = (
                        await self.window_evidence(uow, condition, window, source, now)
                        if window.status == "available"
                        else None
                    )
                    payload = evidence or dict(
                        kind="consumo",
                        result=result,
                        reason_code=window.reason_code or "origen_no_homogeneo",
                        source_mode=window.source_mode,
                        source_revision=source["configuration_revision"],
                        owner_capture=window.model_dump(mode="json"),
                    )
                    made += await self.record(
                        uow,
                        version,
                        activation,
                        state,
                        key,
                        result,
                        payload,
                        evidence,
                        window=window,
                    )
            await uow.commit()
            return made

    async def window_evidence(self, uow, condition, window, source, now):
        """Copy owner's exact total, homogeneous origin and captured calculation basis without recomputing energy."""
        bases = sorted(
            {
                cat
                for segment in window.configuration_segments
                for cat in segment.base_categories
            }
        )
        from sqlalchemy import func

        from ecs_ec.consumption.models import IncorporatedRecord

        received = await uow.session.scalar(
            select(func.max(IncorporatedRecord.first_incorporated_at)).where(
                IncorporatedRecord.id.in_(window.record_refs)
            )
        )
        return validate(
            "Evidence",
            dict(
                category_id=condition["category_id"],
                window=dict(
                    start=stamp(window.period.start), end=stamp(window.period.end)
                ),
                unit="kWh",
                value_kwh=window.energy_kwh,
                quality="valida",
                origin="calculado"
                if window.source_mode in {"calculated", "mixed"}
                else "medido",
                basis_categories=bases,
                scope_description="Agregado del propietario con tramos medidos y calculados; la base indicada corresponde solo a los tramos calculados. No equivale a una medición física general única."
                if window.source_mode == "mixed"
                else "Total de las categorías de base indicadas; no equivale a una medición física general."
                if bases
                else "Medición de la categoría y período indicados.",
                source_refs=[
                    dict(
                        module="consumption",
                        entity_id=str(identifier),
                        revision=window.evidence_revision,
                    )
                    for identifier in window.record_refs
                ],
                formula_version=None,
                received_at=stamp(received) if received else None,
                detected_at=stamp(now),
                limitation_code=None,
            ),
        )

    def absence_evidence(self, condition, source, baseline, now):
        """A silence interval has no energy value; its logical source/base and acceptance baseline remain explicit."""
        return validate(
            "Evidence",
            dict(
                category_id=condition["category_id"],
                window=dict(start=stamp(baseline), end=stamp(now)),
                unit="kWh",
                value_kwh=None,
                quality="sin_fuente"
                if source["source_mode"] == "unavailable"
                else "sin_datos",
                origin={
                    "measured": "medido",
                    "calculated": "calculado",
                    "unavailable": "sin_fuente",
                }[source["source_mode"]],
                basis_categories=list(source["base_categories"]),
                scope_description="Disponibilidad de datos nuevos de la fuente o del total válido; no mide consumo cero.",
                source_refs=[],
                formula_version=None,
                received_at=stamp(source["last_new_data_at"])
                if source["last_new_data_at"]
                else None,
                detected_at=stamp(now),
                limitation_code="sin_novedades_aceptadas_en_plazo",
            ),
        )

    async def record(
        self,
        uow,
        version,
        activation,
        state,
        key,
        result,
        payload,
        evidence,
        *,
        event=None,
        window=None,
    ):
        """Deduplicate before transitions; only a new valid evaluation advances the normalizing cursor."""
        if await uow.session.scalar(
            select(models.Evaluation.id).where(
                models.Evaluation.activation_id == activation.id,
                models.Evaluation.evidence_key == key,
            )
        ):
            return 0
        now = self.service.clock.now()
        retain = anniversary(now, self.service.identity.timezone)
        proof_id = uuid4()
        fields = (
            dict(
                value_kwh=evidence["value_kwh"],
                origin=evidence["origin"],
                limitation_code=evidence["limitation_code"],
                category_id=evidence["category_id"],
                window_start=instant(evidence["window"]["start"]),
                window_end=instant(evidence["window"]["end"]),
                cutoff_at=now,
                source_refs=evidence["source_refs"],
            )
            if evidence
            else dict(
                origin="sin_fuente",
                limitation_code="no_evaluable"
                if result == "no_evaluable"
                else "evento_funcional",
                cutoff_at=now,
            )
        )
        # SQL Numeric receives Decimal, preserving exact textual owner energy.
        if fields.get("value_kwh") is not None:
            from decimal import Decimal

            fields["value_kwh"] = Decimal(fields["value_kwh"])
        uow.session.add(
            models.Evidence(
                id=proof_id,
                payload=payload,
                created_at=now,
                retain_until=retain,
                **fields,
            )
        )
        episode = (
            await uow.session.get(models.Episode, state.open_episode_id)
            if state.open_episode_id
            else None
        )
        opened = False
        if result == "cumple" and (event or episode is None):
            episode = models.Episode(
                id=uuid4(),
                activation_id=activation.id,
                scope_key=state.scope_key,
                opened_at=now,
                closed_at=now if event else None,
                opening_evidence_id=proof_id,
                source_event_id=event.id if event else None,
                status="cerrado" if event else "abierto",
                created_at=now,
                retain_until=retain,
            )
            uow.session.add(episode)
            opened = True
            if not event:
                state.open_episode_id = episode.id
        elif result == "no_cumple" and episode:
            episode.status = "cerrado"
            episode.closed_at = now
            episode.closing_evidence_id = proof_id
            episode.retain_until = max(episode.retain_until, retain)
            state.open_episode_id = None
            opening = await uow.session.get(
                models.Evidence, episode.opening_evidence_id, with_for_update=True
            )
            opening.retain_until = max(opening.retain_until, episode.retain_until)
        if result in {"cumple", "no_cumple"} and window and window.period:
            state.last_valid_window_end = window.period.end
            state.source_cursor = window.cursor
        if window and window.period:
            state.last_evaluated_window_end = window.period.end
        if result != "omitida_historica":
            state.last_result = result
        uow.session.add(
            models.Evaluation(
                id=uuid4(),
                activation_id=activation.id,
                source_event_id=event.id if event else None,
                evidence_key=key,
                window_start=window.period.start if window and window.period else None,
                window_end=window.period.end if window and window.period else None,
                cutoff_at=now,
                evaluated_at=now,
                result=result,
                reason_code="condicion_" + result,
                evidence_id=proof_id,
                episode_id=episode.id if episode else None,
                created_at=now,
                retain_until=retain,
            )
        )
        version.retain_until = max(version.retain_until, retain)
        if opened:
            await self.materialize(
                uow, version, activation, episode, evidence, event, now, retain
            )
        return 1

    async def materialize(
        self, uow, version, activation, episode, evidence, event, now, retain
    ):
        """New episode/point event creates its sole captured message and per-account deliveries in this UoW."""
        from ecs_ec.notifications.content import urgent_content

        content = await urgent_content(
            self.service, uow, version, episode, evidence, event, now
        )
        period = content["window"]
        oid, mid = uuid4(), uuid4()
        uow.session.add(
            models.Occurrence(
                id=oid,
                version_id=version.id,
                activation_id=activation.id,
                kind="urgente",
                logical_key="episode:" + str(episode.id),
                detected_at=now,
                window_start=instant(period["start"]) if period else None,
                window_end=instant(period["end"]) if period else None,
                cutoff_at=now,
                episode_id=episode.id,
                tzdata_version=activation.tzdata_version,
                is_late=content["is_late"],
                created_at=now,
                retain_until=retain,
            )
        )
        uow.session.add(
            models.Message(
                id=mid,
                occurrence_id=oid,
                functional_content=content,
                content_hash=digest(content),
                required_permissions=list(required_permissions(version.config)),
                created_at=now,
                retain_until=retain,
            )
        )
        for raw in version.config["recipient_ids"]:
            identifier = uuid4()
            uow.session.add(
                models.Delivery(
                    id=identifier,
                    message_id=mid,
                    account_id=UUID(raw),
                    next_attempt_at=now,
                    smtp_message_id=f"<{identifier}@{self.service.settings.mail_from.rsplit('@', 1)[1]}>",
                    transport_kind=self.service.settings.mail_transport,
                    created_at=now,
                    retain_until=retain,
                )
            )
