"""Trusted002 admission with immutable attempts and independent durable category transactions."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from ecs_ec.audit.events import Code, EventInput, EventWriter, Interval, PayloadRegistry, SafePayload
from ecs_ec.consumption.catalog import CATEGORY_IDS
from ecs_ec.consumption.catalog_storage import configuration_segments
from ecs_ec.consumption.models import (CategoryId, CategoryUpdate, DomainModel, IncorporatedRecord, ReceptionAttempt,
    ReceptionRecordResult, ReceptionResult, TotalEvaluationRequest)
from ecs_ec.consumption.ports import AttemptLookup, CategoryUpdateResult, ReceptionOutcome
from ecs_ec.consumption.store import advance_state, classify, incorporate_measurement, lock_history
from ecs_ec.consumption.validation import MeasurementError, MeasurementValidator, RawMeasurement
from ecs_ec.core.clock import utc
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork


class ReceptionError(ValueError):
    """Stable safe boundary error; caller distinguishes it from infrastructure failure."""

    def __init__(self, code):
        """Expose a fixed code without input bodies, secrets or database exception text."""
        self.code = code
        super().__init__(code)


class InputAtom(DomainModel):
    """Lossless typed scalar in a frozen trusted-adapter manifest, including invalid raw numeric inputs."""

    type: Literal['null', 'bool', 'int', 'float', 'decimal', 'uuid', 'datetime', 'str']
    text: str | None


class InputRecord(DomainModel):
    """Position-stable allowlisted raw fields; arbitrary nested bodies/tokens cannot enter the manifest."""

    position: int = Field(ge=0)
    fields: dict[Literal['building_id', 'category_id', 'source_id', 'start', 'end', 'value', 'unit',
        'source_evidence_ref', 'correlation_ref'], InputAtom]


class InputManifest(DomainModel):
    """Canonical complete invocation input, independent from call time and authorization credentials."""

    schema_version: Literal[1] = 1
    building_id: UUID
    publication_ref: str = Field(min_length=1, max_length=200)
    process: str = Field(min_length=1, max_length=200)
    correlation_ref: str = Field(pattern=r'^[A-Za-z0-9_.:/-]{1,200}$')
    records: tuple[InputRecord, ...]


def _atom(value):
    """Encode a supported raw scalar without float conversion or bool/int equality ambiguity."""
    types = {type(None): 'null', bool: 'bool', int: 'int', float: 'float', Decimal: 'decimal', UUID: 'uuid', datetime: 'datetime', str: 'str'}
    kind = types.get(type(value))
    if kind is None: raise ReceptionError('invalid_attempt_input')
    rendered = value.isoformat() if kind == 'datetime' else str(value) if kind != 'null' else None
    return InputAtom(type=kind, text=rendered)


def _manifest(building_id, publication_ref, process, records, correlation_ref):
    """Freeze all ordered input scalars before any category result; reject unsupported envelopes."""
    try:
        result = InputManifest(building_id=building_id, publication_ref=publication_ref, process=process,
            correlation_ref=correlation_ref, records=tuple(InputRecord(position=i,
                fields={key: _atom(value) for key, value in record.items()}) for i, record in enumerate(records)))
    except (ValueError, TypeError, AttributeError): raise ReceptionError('invalid_attempt_input') from None
    data = result.model_dump(mode='json')
    encoded = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return data, hashlib.sha256(encoded.encode()).hexdigest()


class CategoryPayload(SafePayload):
    """Functional update evidence permits only codes, IDs, counts and exact measured windows."""

    building_id: UUID
    category_id: CategoryId
    kind: Literal['physical', 'calculated']
    accepted_count: int
    duplicate_count: int
    rejected_count: int
    reason_codes: list[Code]
    record_ids: list[UUID]
    windows: list[Interval]


async def append_update_events(uow, update, records, reason_codes, correlation_ref, clock, timezone):
    """Append deduplicated009 events atomically; summary recovery never calls this again."""
    payload = CategoryPayload(building_id=update.building_id, category_id=update.category_id, kind=update.kind,
        accepted_count=update.accepted_count, duplicate_count=update.duplicate_count, rejected_count=update.rejected_count,
        reason_codes=sorted(set(reason_codes)), record_ids=[r.id for r in records],
        windows=[Interval(start=r.start, end=r.end) for r in records])
    registry = PayloadRegistry()
    for code in ('consumption.accepted', 'reception.completed'): registry.register(code, CategoryPayload)
    writer = EventWriter(registry, clock, timezone)
    codes = (['consumption.accepted'] if records else []) + (['reception.completed'] if update.kind == 'physical' else [])
    window = Interval(start=min(r.start for r in records), end=max(r.end for r in records)) if records else None
    for code in codes:
        await writer.append(uow, EventInput(event_id=uuid4(), event_type=code, source_module='consumption',
            source_entity_id=update.id, source_revision=update.revision, occurred_at=update.evaluated_at,
            measurement_window=window, accepted_new_data=bool(records), safe_payload=payload.model_dump(), correlation_ref=correlation_ref))


async def request_total_evaluation(uow, row, update, now, timezone, revisions):
    """Create/reactivate durable work in the partial's own transaction, even before any candidate."""
    if row.category_id == 'CAT-01': return
    segments = configuration_segments(revisions, 'CAT-01', row.start, row.end)
    if not any(s.source_mode == 'calculated' and row.category_id in s.base_categories for s in segments): return
    request = await uow.session.scalar(select(TotalEvaluationRequest).where(TotalEvaluationRequest.building_id == row.building_id,
        TotalEvaluationRequest.start == row.start, TotalEvaluationRequest.end == row.end).with_for_update())
    deadline = anniversary(now, timezone)
    if request is None:
        request = TotalEvaluationRequest(id=uuid4(), building_id=row.building_id, start=row.start, end=row.end, revision=1,
            status='pending', created_at=now, updated_at=now, processed_at=None, trigger_update_id=update.id,
            correlation_ref=row.correlation_ref, retain_until=deadline)
        uow.session.add(request)
    else:
        request.status, request.processed_at = 'pending', None
        request.updated_at, request.trigger_update_id, request.correlation_ref = now, update.id, row.correlation_ref
        request.revision += 1
        request.retain_until = max(request.retain_until, deadline)
    await uow.session.flush()


class Reception:
    """Trusted in-process port; configured process→building capabilities authorize before DB lookup."""

    def __init__(self, database, clock, *, authorized_processes):
        """Inject009 resources and explicit trusted bindings; never infer permissions from record content."""
        self.database, self.clock = database, clock
        self.authorized_processes = {p: frozenset(ids) for p, ids in authorized_processes.items()}
        self.validator = MeasurementValidator()

    def _authorize(self, process, building_id):
        """Refuse unbound technical callers before distinguishing an attempt's existence."""
        if building_id not in self.authorized_processes.get(process, ()): raise ReceptionError('unauthorized_process')

    async def read_attempt(self, attempt_id, building_id, process) -> AttemptLookup:
        """Read one coherent durable capture without accepting/resuming or extending any deadline."""
        self._authorize(process, building_id)
        return await self._capture(self.database.sessions, attempt_id, building_id, process)

    async def _capture(self, sessions, attempt_id, building_id, process):
        """Copy one read-only capture, optionally on the exclusively held attempt connection."""
        async with UnitOfWork(sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            return await self._lookup(uow, attempt_id, building_id, process)

    async def _lookup(self, uow, attempt_id, building_id, process):
        """Copy attempt/results/updates in a single snapshot; database errors propagate explicitly."""
        attempt = await uow.session.get(ReceptionAttempt, attempt_id)
        if attempt is None: return AttemptLookup(attempt_id=attempt_id, building_id=building_id, state='not_found', outcome=None)
        if attempt.building_id != building_id or attempt.process_ref != process: raise ReceptionError('attempt_context_conflict')
        rows = (await uow.session.scalars(select(ReceptionRecordResult).where(ReceptionRecordResult.attempt_id == attempt_id)
            .order_by(ReceptionRecordResult.input_position))).all()
        updates = (await uow.session.scalars(select(CategoryUpdate).where(CategoryUpdate.attempt_id == attempt_id)
            .order_by(CategoryUpdate.category_id))).all()
        referenced = [r.record_id for r in rows if r.record_id]
        records = {r.id: r for r in (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.id.in_(referenced)))).all()}
        results = tuple(ReceptionResult(position=r.input_position, status=r.status, reason_code=r.reason_code,
            measurement_id=r.record_id, measurement_revision=records[r.record_id].revision if r.record_id else None,
            category_revision=records[r.record_id].category_revision if r.record_id else None,
            category_id=r.category_id, next_admissible_at=r.next_admissible_at, correlation_ref=attempt.correlation_ref,
            first_incorporated_at=records[r.record_id].first_incorporated_at if r.record_id else None) for r in rows)
        summaries = tuple(CategoryUpdateResult(**{field: getattr(r, field) for field in CategoryUpdateResult.model_fields}) for r in updates)
        done = {r.input_position for r in rows}
        outcome = ReceptionOutcome(attempt_id=attempt_id, building_id=building_id, correlation_ref=attempt.correlation_ref,
            received_at=attempt.received_at, completed_at=attempt.completed_at, state=attempt.status,
            results=results, updates=summaries, pending_positions=tuple(i for i in range(len(attempt.input_manifest['records'])) if i not in done))
        return AttemptLookup(attempt_id=attempt_id, building_id=building_id, state=attempt.status, outcome=outcome)

    async def accept(self, attempt_id, building_id, publication_ref, process, records, correlation_ref) -> ReceptionOutcome:
        """Freeze input, recover only missing category transactions, return only committed classifications.

        A session advisory lock holds exclusive control across category commits on the
        same connection. Waiting holds no context/category locks. Reusing that connection
        prevents pool exhaustion by coordinators waiting for a second connection. A crash
        releases the lock; cancellation invalidates any connection whose unlock fails.
        """
        self._authorize(process, building_id)
        attempt_id = UUID(str(attempt_id))
        # Consume caller-owned input once before any await, without retaining mutable containers.
        try: records = tuple(dict(r) for r in records)
        except (TypeError, ValueError): raise ReceptionError('invalid_attempt_input') from None
        manifest, digest = _manifest(building_id, publication_ref, process, records, correlation_ref)
        lock_key = int.from_bytes(hashlib.sha256(b'consumption-attempt:' + attempt_id.bytes).digest()[:8], 'big', signed=True)
        async with self.database.engine.connect() as coordinator:
            try:
                await coordinator.execute(text('SELECT pg_advisory_lock(:key)'), {'key': lock_key})
                await coordinator.commit()
            except BaseException:
                await coordinator.invalidate()
                raise
            sessions = async_sessionmaker(coordinator, expire_on_commit=False)
            try:
                return await self._accept_locked(sessions, attempt_id, building_id, publication_ref, process, records, correlation_ref, manifest, digest)
            finally:
                try:
                    await coordinator.rollback()
                    await coordinator.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': lock_key})
                    await coordinator.commit()
                except BaseException:
                    await coordinator.invalidate()
                    raise

    async def _accept_locked(self, sessions, attempt_id, building_id, publication_ref, process, records, correlation_ref, manifest, digest):
        """Recover one attempt while exclusively owning its connection; categories still commit independently."""
        async with UnitOfWork(sessions) as uow:
            attempt = await uow.session.get(ReceptionAttempt, attempt_id)
            if attempt:
                # Compare complete canonical structure AND digest. Types are explicit atoms.
                if attempt.input_digest != digest or attempt.input_manifest != manifest: raise ReceptionError('attempt_payload_conflict')
                if attempt.status == 'completed': return (await self._lookup(uow, attempt_id, building_id, process)).outcome
                attempt.status = 'processing'
                attempt.completed_at = None
            else:
                from ecs_ec.consumption.catalog_storage import BuildingRow
                building = await uow.session.get(BuildingRow, building_id)
                if building is None: raise ReceptionError('building_context_missing')
                now = utc(self.clock.now())
                uow.session.add(ReceptionAttempt(id=attempt_id, building_id=building_id, publication_ref=publication_ref,
                    process_ref=process, correlation_ref=correlation_ref, received_at=now, status='processing', completed_at=None,
                    input_schema_version=1, input_manifest=manifest, input_digest=digest, retain_until=anniversary(now, building.timezone)))
            await uow.commit()
        try:
            snapshot = await self._capture(sessions, attempt_id, building_id, process)
            missing = set(snapshot.outcome.pending_positions)
            for category in (*CATEGORY_IDS, None):
                positions = [(i, r) for i, r in enumerate(records) if i in missing
                    and (r.get('category_id') if r.get('category_id') in CATEGORY_IDS else None) == category]
                if positions: await self._category(attempt_id, building_id, category, positions, correlation_ref, sessions)
            await self._evaluate(building_id, sessions)
            await self._complete(attempt_id, sessions)
        except Exception:
            # Previously committed categories survive. A DB failure may also prevent this
            # summary write; processing remains recoverable and no success is reported.
            try:
                async with UnitOfWork(sessions) as uow:
                    attempt = await uow.session.get(ReceptionAttempt, attempt_id)
                    attempt.status, attempt.completed_at = 'partial_failure', None
                    await uow.commit()
            except Exception: pass
            raise
        return (await self._capture(sessions, attempt_id, building_id, process)).outcome

    async def _evaluate(self, building_id, sessions):
        """Evaluate committed partial work using the same coordinator connection, before final summary."""
        from ecs_ec.consumption.pending_totals import PendingTotals
        await PendingTotals(self.database, self.clock, sessions=sessions).run_due(building_id)

    async def _complete(self, attempt_id, sessions=None):
        """Finalize summary only after all positions commit; a failed summary can be reconstructed."""
        async with UnitOfWork(sessions or self.database.sessions) as uow:
            attempt = await uow.session.get(ReceptionAttempt, attempt_id)
            positions = (await uow.session.scalars(select(ReceptionRecordResult.input_position).where(ReceptionRecordResult.attempt_id == attempt_id))).all()
            if set(positions) != set(range(len(attempt.input_manifest['records']))): raise ReceptionError('attempt_incomplete')
            attempt.status, attempt.completed_at = 'completed', utc(self.clock.now())
            await uow.commit()

    async def _category(self, attempt_id, building_id, category, positions, correlation_ref, sessions=None):
        """Validate/classify before timing; commit one independent category with results/aggregates/events/work."""
        async with UnitOfWork(sessions or self.database.sessions) as uow:
            building, states, global_state, revisions = await lock_history(uow, building_id)
            now = utc(self.clock.now())
            deadline = anniversary(now, building.timezone)
            state = states.get(category)
            update = None
            if category:
                update = CategoryUpdate(id=uuid4(), attempt_id=attempt_id, building_id=building_id, category_id=category,
                    kind='physical', evaluated_at=now, new_data_at=None, previous_new_data_at=state.last_new_data_at,
                    next_admissible_at=state.next_admissible_at, accepted_count=0, duplicate_count=0, rejected_count=0,
                    revision=1, retain_until=deadline)
                uow.session.add(update)
                await uow.session.flush()
            classified, proposed = [], []
            for position, data in positions:
                try:
                    raw = RawMeasurement.model_validate(data)
                    if raw.building_id != building_id: raise MeasurementError('source_building_mismatch')
                    measurement = self.validator.normalize(data, configuration_segments(revisions, category, raw.start, raw.end))
                    status, reference = await classify(uow, measurement)
                    if status == 'new':
                        for previous_position, previous in proposed:
                            if previous.start < measurement.end and previous.end > measurement.start:
                                if previous.source_id == measurement.source_id and previous.start == measurement.start and previous.end == measurement.end:
                                    status = 'batch_duplicate' if previous.energy_kwh == measurement.energy_kwh else 'conflicting_duplicate'
                                    reference = previous_position
                                else: status = 'overlapping_interval'
                                break
                    if status == 'new': proposed.append((position, measurement))
                    classified.append((position, status, reference, measurement))
                except MeasurementError as error: classified.append((position, error.code, None, None))
                except ValueError: classified.append((position, 'unknown_category' if category is None else 'invalid_measurement', None, None))
            early = state and state.next_admissible_at and now < state.next_admissible_at
            clock_regressed = state and state.last_new_data_at and now < state.last_new_data_at
            accepted, by_position, outcomes = [], {}, []
            for position, status, reference, measurement in classified:
                row, reason = None, None
                if status in ('new', 'batch_duplicate') and early:
                    reason = 'clock_regressed' if clock_regressed else 'too_early'
                elif status == 'new':
                    try:
                        async with uow.session.begin_nested():
                            row = await incorporate_measurement(uow, measurement, update, now, building.timezone)
                    except IntegrityError as error:
                        if getattr(error.orig, 'sqlstate', None) not in ('23505', '23P01') or getattr(getattr(error.orig, 'diag', None), 'constraint_name', None) not in ('uq_record_physical', 'uq_record_calculated', 'ex_record_overlap'): raise
                        result, row = await classify(uow, measurement)
                        if result != 'duplicate': reason, row = result, None
                        else: status = 'duplicate'
                    else:
                        accepted.append(row)
                        by_position[position] = row
                elif status == 'batch_duplicate': row = by_position[reference]
                elif status == 'duplicate': row = reference
                else: reason = status
                if row is not None: by_position[position] = row
                disposition = 'rejected' if reason else 'accepted' if status == 'new' else 'duplicate'
                outcomes.append((position, disposition, reason, row))
            if update:
                advance_state(state, global_state, accepted, now)
                update.accepted_count = len(accepted)
                update.duplicate_count = sum(s == 'duplicate' for _, s, _, _ in outcomes)
                update.rejected_count = sum(s == 'rejected' for _, s, _, _ in outcomes)
                update.new_data_at = now if accepted else None
                update.next_admissible_at = state.next_admissible_at
                for row in accepted: await request_total_evaluation(uow, row, update, now, building.timezone, revisions)
            for position, status, reason, row in outcomes:
                uow.session.add(ReceptionRecordResult(id=uuid4(), attempt_id=attempt_id, category_update_id=update.id if update else None,
                    input_position=position, category_id=category, record_id=row.id if row else None, status=status, reason_code=reason,
                    next_admissible_at=state.next_admissible_at if state else None, recorded_at=now, retain_until=deadline))
            if update: await append_update_events(uow, update, accepted, [r for _, _, r, _ in outcomes if r], correlation_ref, self.clock, building.timezone)
            await uow.commit()
