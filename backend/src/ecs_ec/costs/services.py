"""004 orchestration: current006 authorization, serialized mutations, coherent inputs and atomic009 evidence."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text, tuple_

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.retention import anniversary
from ecs_ec.consumption.catalog_storage import lock_configuration
from ecs_ec.costs import engine
from ecs_ec.costs.adapters import Evidence
from ecs_ec.costs.models import Supply, BillingCycle, InputSnapshot, Calculation, CalculationComponent
from ecs_ec.costs.money import digest, number
from ecs_ec.costs.repository import CostsProblem, replay, remember, view
from ecs_ec.costs.schemas import CalculateRequest
from ecs_ec.costs.snapshots import capture
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account, Session
from ecs_ec.identity.schemas import Principal


class EngineFailure(Exception):
    """Internal signal carrying already captured inputs only; the original exception is never persisted."""

    def __init__(self, evidence):
        """Keep validated inputs for a new valid result/event transaction after the first UoW rolls back."""
        self.evidence = evidence


class Costs:
    """Singleton financial facade composed with actual001/002 consumption and006 identity providers."""

    def __init__(self, database, clock, identity, consumption):
        """Inject common resources without SMTP,008 consumers or a separately deployed worker."""
        self.database, self.clock, self.identity, self.consumption = database, clock, identity, consumption
        self.building_id = identity.settings.building_id
        self.timezone = identity.timezone
        self.evidence = Evidence(clock, self.timezone)

    def authorize(self, principal, action='costs.read'):
        """Apply006's current request-local principal; durable mutations additionally revalidate under locks."""
        self.identity.authorize(principal, action, self.building_id)

    async def _mutate(self, principal, action, operation, key, body, handler):
        """Lock/revalidate account→session→building, then replay or atomically commit handler/result/evidence."""
        self.authorize(principal, action)
        actor_ref = f'account:{principal.account_id}'
        async with UnitOfWork(self.database.sessions) as uow:
            account = await uow.session.scalar(select(Account).where(Account.id == principal.account_id).with_for_update())
            session = await uow.session.scalar(select(Session).where(Session.id == principal.session_id).with_for_update())
            if not self.identity.session_valid(account, session, self.clock.now()):
                raise IdentityProblem('session_required', 401)
            current = Principal.from_rows(account, session, self.building_id)
            self.authorize(current, action)
            building = await lock_configuration(uow, self.building_id)
            if building is None:
                raise CostsProblem('building_context_missing', 503)
            old = await replay(uow, actor_ref, operation, key, body)
            if old:
                return old.response, old.http_status
            response, status = await handler(uow, actor_ref)
            await remember(uow, actor_ref, operation, key, body, response, status, self.clock, self.timezone)
            now = self.clock.now()
            session.last_activity_at = max(session.last_activity_at, now)
            session.idle_expires_at = min(session.absolute_expires_at, session.last_activity_at + timedelta(minutes=30))
            await uow.commit()
            return response, status

    async def get_supply(self, principal):
        """Read administrative current supply only; a missing configuration is404, never implicitly created."""
        self.authorize(principal, 'costs.configuration.read')
        async with UnitOfWork(self.database.sessions) as uow:
            supply = await uow.session.scalar(select(Supply).where(Supply.building_id == self.building_id))
            if supply is None:
                raise CostsProblem('supply_missing', 404)
            return view(supply)

    async def calculate(self, principal, request, key):
        """Authorize/idempotently capture and persist a real revision; only engine failures enter a fresh failure UoW."""
        request = CalculateRequest.model_validate(request)
        body = request.model_dump(mode='json')
        async def run(uow, actor_ref):
            """Read stable actual inputs while holding the common building lock, then evaluate and persist."""
            supply = await uow.session.get(Supply, request.supply_id)
            if supply is None or supply.building_id != self.building_id:
                raise CostsProblem('supply_not_found', 404)
            if request.timezone != self.timezone:
                raise CostsProblem('invalid_timezone', 422)
            async with UnitOfWork(self.database.sessions) as read:
                await read.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                inputs = await capture(read, consumption=self.consumption, supply_id=supply.id, request=request, cutoff_at=self.clock.now())
            try:
                result = engine.evaluate(inputs)
            except CostsProblem:
                raise
            except Exception:
                raise EngineFailure(inputs) from None
            return await self._save_calculation(uow, actor_ref, inputs, result), 201
        try:
            return await self._mutate(principal, 'costs.calculations.create', 'calculation.create', key, body, run)
        except EngineFailure as failure:
            inputs = failure.evidence
            async def failed(uow, actor_ref):
                """Persist a sanitized failed result and cost.failed together after the aborted attempt's rollback."""
                result = dict(execution_state='fallido', temporal_state='cerrado' if request.end <= inputs.cutoff_at and not request.boundary_limited else 'en_curso',
                    sufficiency='no_calculable', available_subtotal='0', complete_total=None, net_total=None, tax_total=None,
                    currency='CLP', reason_codes=['engine_failed'], components=[], monthly_maxima=[])
                return await self._save_calculation(uow, actor_ref, inputs, result), 201
            try:
                return await self._mutate(principal, 'costs.calculations.create', 'calculation.create', key, body, failed)
            except (CostsProblem, IdentityProblem):
                raise
            except Exception:
                raise CostsProblem('failure_result_not_persisted', 503) from None

    async def _save_calculation(self, uow, actor_ref, inputs, result):
        """Append cycle/snapshot/result/components/audit/event in one UoW, preserving every prior revision."""
        request, now = inputs.request, self.clock.now()
        deadline = anniversary(now, request.timezone)
        retained = dict(created_at=now, actor_ref=actor_ref, retain_until=deadline)
        cycle = await uow.session.scalar(select(BillingCycle).where(BillingCycle.supply_id == inputs.supply_id,
            BillingCycle.start_at == request.start, BillingCycle.end_at == request.end).with_for_update())
        if cycle is None:
            cycle = BillingCycle(id=uuid4(), supply_id=inputs.supply_id, start_at=request.start, end_at=request.end,
                timezone=request.timezone, data=dict(boundary_criterion=request.boundary_criterion, boundary_limited=request.boundary_limited,
                    declared_start=request.declared_start, declared_end=request.declared_end), **retained)
            uow.session.add(cycle)
            await uow.session.flush()
        previous = await uow.session.scalar(select(Calculation).where(Calculation.cycle_id == cycle.id).order_by(Calculation.revision.desc()).limit(1))
        if previous and not request.reason:
            raise CostsProblem('recalculation_reason_required', 422)
        snapshot = InputSnapshot(id=uuid4(), cycle_id=cycle.id, profile_version_id=inputs.profile_id,
            cutoff_at=inputs.cutoff_at, schema_version=1, engine_version=engine.ENGINE_VERSION,
            input_hash=digest(dict(engine_version=engine.ENGINE_VERSION, inputs=inputs.model_dump(mode='json'))),
            data=inputs.model_dump(mode='json'), monthly_maxima=result['monthly_maxima'], **retained)
        uow.session.add(snapshot)
        await uow.session.flush()
        row = Calculation(id=uuid4(), cycle_id=cycle.id, revision=previous.revision + 1 if previous else 1,
            previous_id=previous.id if previous else None, snapshot_id=snapshot.id, cutoff_at=inputs.cutoff_at,
            execution_state=result['execution_state'], temporal_state=result['temporal_state'], sufficiency=result['sufficiency'],
            available_subtotal=number(result['available_subtotal']), complete_total=number(result['complete_total']) if result['complete_total'] is not None else None,
            data=result, **retained)
        uow.session.add(row)
        await uow.session.flush()
        for component in result['components']:
            uow.session.add(CalculationComponent(id=uuid4(), calculation_id=row.id, code=component['code'],
                basis_value=number(component['basis_value']) if component['basis_value'] is not None else None,
                presented_amount=number(component['presented_amount']) if component['presented_amount'] is not None else None,
                data=component, **retained))
        # References live permanently; evidence and currently required parents must never have a shorter minimum.
        from ecs_ec.costs.models import ProfileVersion
        for parent in (cycle, await uow.session.get(Supply, inputs.supply_id), await uow.session.get(ProfileVersion, inputs.profile_id) if inputs.profile_id else None):
            if parent is not None:
                parent.retain_until = max(parent.retain_until, deadline)
        from ecs_ec.costs.retention import protect
        await protect(uow, row, deadline)
        await self.evidence.append(uow, building_id=self.building_id, row=row, action='costs.calculation.created',
            failed=row.execution_state == 'fallido', window=request)
        return await self._calculation_view(uow, row)

    async def _calculation_view(self, uow, row):
        """Detach persisted result/evidence; read paths never run the engine or alter retention."""
        snapshot = await uow.session.get(InputSnapshot, row.snapshot_id)
        from ecs_ec.costs.schemas import CalculationDetail
        data = view(row) | dict(cycle_id=str(row.cycle_id), snapshot_id=str(snapshot.id),
            previous_id=str(row.previous_id) if row.previous_id else None, cutoff_at=row.cutoff_at.isoformat(),
            snapshot=snapshot.data, input_hash=snapshot.input_hash, engine_version=snapshot.engine_version)
        return CalculationDetail.model_validate(data).model_dump(mode='json')

    async def get_calculation(self, principal, identifier):
        """Read a calculation only through its configured building, hiding nonexistent or foreign resources."""
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            row = await uow.session.scalar(select(Calculation).join(BillingCycle).join(Supply).where(Calculation.id == identifier, Supply.building_id == self.building_id))
            if row is None:
                raise CostsProblem('calculation_not_found', 404)
            return await self._calculation_view(uow, row)

    async def cycles(self, principal, *, start=None, end=None, cutoff_at=None, limit=25, cursor=None):
        """Read actual cycles and latest visible calculations, with a fixed cutoff and deterministic continuation."""
        self.authorize(principal)
        if not 1 <= limit <= 100:
            raise CostsProblem('invalid_limit', 422)
        from ecs_ec.identity.pagination import encode_cursor, decode_cursor
        from ecs_ec.consumption.models import instant
        filters = dict(start=start.isoformat() if start else None, end=end.isoformat() if end else None,
            cutoff_at=cutoff_at.isoformat() if cutoff_at else None, building_id=str(self.building_id))
        last = decode_cursor(self.identity.settings, cursor, 'costs.cycles', filters) if cursor else None
        cutoff = instant(last['cutoff']) if last else cutoff_at or self.clock.now()
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            query = select(BillingCycle).join(Supply).where(Supply.building_id == self.building_id, BillingCycle.created_at <= cutoff)
            if start:
                query = query.where(BillingCycle.end_at > start)
            if end:
                query = query.where(BillingCycle.start_at < end)
            if last:
                try:
                    query = query.where(tuple_(BillingCycle.start_at, BillingCycle.id) > tuple_(instant(last['start']), UUID(last['id'])))
                except (ValueError, KeyError, TypeError):
                    raise CostsProblem('invalid_cursor', 422) from None
            fetched = (await uow.session.scalars(query.order_by(BillingCycle.start_at, BillingCycle.id).limit(limit+1))).all()
            cycles = fetched[:limit]
            items = []
            for cycle in cycles:
                from ecs_ec.costs.history import cycle_view
                items.append((await cycle_view(self, uow, cycle, cutoff)).model_dump(mode='json'))
            continuation = encode_cursor(self.identity.settings, 'costs.cycles', filters,
                dict(start=cycles[-1].start_at.isoformat(), id=str(cycles[-1].id), cutoff=cutoff.isoformat())) if len(fetched) > limit else None
            return dict(items=items, next_cursor=continuation, cutoff_at=cutoff.isoformat())

    async def save_bill(self, principal, command, key, *, bill_id=None, if_match=None):
        """Register/correct a manual invoice, with current permission and optimistic preconditions after replay."""
        from ecs_ec.costs.schemas import BillInput
        from ecs_ec.costs.bills import append_bill
        from ecs_ec.costs.models import Bill, BillRevision
        command = BillInput.model_validate(command)
        async def run(uow, actor_ref):
            """Validate scope/precondition and append one immutable bill revision, without touching measurements/profile."""
            supply = await uow.session.get(Supply, command.supply_id)
            if supply is None or supply.building_id != self.building_id:
                raise CostsProblem('supply_not_found', 404)
            if command.timezone != self.timezone:
                raise CostsProblem('invalid_timezone', 422)
            expected = None
            if bill_id:
                logical = await uow.session.get(Bill, bill_id)
                if logical is None or logical.supply_id != supply.id:
                    raise CostsProblem('bill_not_found', 404)
                latest = await uow.session.scalar(select(BillRevision).where(BillRevision.bill_id == bill_id).order_by(BillRevision.revision.desc()).limit(1))
                require_match(if_match, 'bill', bill_id, latest.revision)
                expected = latest.revision
            row, created = await append_bill(uow, supply, command, actor_ref, self.clock, bill_id=bill_id, expected_revision=expected)
            from ecs_ec.costs.retention import protect
            await protect(uow, row, row.retain_until)
            if bill_id or created:
                await self.evidence.append(uow, building_id=self.building_id, row=row, action='costs.bill.created')
            return self._bill_view(row), 201 if created else 200
        return await self._mutate(principal, 'costs.bills.manage', f'bill.update:{bill_id}' if bill_id else 'bill.create',
            key, command.model_dump(mode='json'), run)

    def _bill_view(self, row):
        """Detach one immutable document revision while preserving both logical and revision identities."""
        from ecs_ec.costs.schemas import BillDetail
        data = dict(id=str(row.bill_id), bill_revision_id=str(row.id), revision=row.revision, cycle_id=str(row.cycle_id),
            previous_id=str(row.previous_id) if row.previous_id else None, created_at=row.created_at.isoformat(),
            retain_until=row.retain_until.isoformat(), **row.data)
        return BillDetail.model_validate(data).model_dump(mode='json')

    async def get_bill(self, principal, bill_id, revision=None):
        """Read current or explicitly numbered historical bill without creating or updating a comparison."""
        from ecs_ec.costs.models import Bill, BillRevision
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            query = select(BillRevision).join(Bill).join(Supply).where(Bill.id == bill_id, Supply.building_id == self.building_id)
            if revision is not None:
                query = query.where(BillRevision.revision == revision)
            row = await uow.session.scalar(query.order_by(BillRevision.revision.desc()).limit(1))
            if row is None:
                raise CostsProblem('bill_not_found', 404)
            return self._bill_view(row)

    async def bills(self, principal, *, limit=25, cursor=None, cycle_id=None):
        """List immutable revisions with stable IDs so current/historical pairs can be explicitly selected."""
        from ecs_ec.costs.models import Bill, BillRevision
        from ecs_ec.costs.repository import page_rows
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            query = select(BillRevision).join(Bill).join(Supply).where(Supply.building_id == self.building_id)
            if cycle_id:
                query = query.where(BillRevision.cycle_id == cycle_id)
            rows, continuation, cutoff = await page_rows(uow, query, BillRevision, settings=self.identity.settings,
                scope='costs.bills', filters=dict(building_id=str(self.building_id), cycle_id=str(cycle_id) if cycle_id else None),
                limit=limit, cursor=cursor, now=self.clock.now())
            return dict(items=[self._bill_view(row) for row in rows], next_cursor=continuation, cutoff_at=cutoff.isoformat())

    async def create_comparison(self, principal, command, key):
        """Persist only the explicitly requested immutable calculation/bill pair; corrections and GET never invoke this."""
        from ecs_ec.costs.schemas import ComparisonRequest
        from ecs_ec.costs.models import Bill, BillRevision, Comparison, ComparisonLine
        from ecs_ec.costs.comparison import compare
        command = ComparisonRequest.model_validate(command)
        async def run(uow, actor_ref):
            """Validate both sides against this building, capture aligned values and retain all referenced parents."""
            calculation = await uow.session.scalar(select(Calculation).join(BillingCycle).join(Supply).where(
                Calculation.id == command.calculation_id, Supply.building_id == self.building_id))
            bill = await uow.session.scalar(select(BillRevision).join(Bill).join(Supply).where(
                BillRevision.id == command.bill_revision_id, Supply.building_id == self.building_id))
            if calculation is None or bill is None:
                raise CostsProblem('comparison_resource_not_found', 404)
            result = compare(await self._calculation_view(uow, calculation), self._bill_view(bill))
            previous = await uow.session.scalar(select(Comparison).where(Comparison.calculation_id == calculation.id,
                Comparison.bill_revision_id == bill.id).order_by(Comparison.revision.desc()).limit(1))
            now = self.clock.now()
            retained = dict(created_at=now, actor_ref=actor_ref, retain_until=anniversary(now, self.timezone))
            row = Comparison(id=uuid4(), calculation_id=calculation.id, bill_revision_id=bill.id,
                revision=previous.revision + 1 if previous else 1, cutoff_at=now, data=result,
                delta_amount=number(result['delta_amount']) if result['delta_amount'] is not None else None,
                delta_percent=number(result['delta_percent']) if result['delta_percent'] is not None else None, **retained)
            uow.session.add(row)
            await uow.session.flush()
            for pair in result['pairs']:
                uow.session.add(ComparisonLine(id=uuid4(), comparison_id=row.id, code=pair['code'], data=pair,
                    calculated_amount=number(pair['calculated_amount']), billed_amount=number(pair['billed_amount']), **retained))
            for parent in (calculation, bill, await uow.session.get(InputSnapshot, calculation.snapshot_id)):
                parent.retain_until = max(parent.retain_until, row.retain_until)
            from ecs_ec.costs.retention import protect
            await protect(uow, row, row.retain_until)
            await self.evidence.append(uow, building_id=self.building_id, row=row, action='costs.comparison.created')
            return self._comparison_view(row), 201
        return await self._mutate(principal, 'costs.comparisons.create', 'comparison.create', key, command.model_dump(mode='json'), run)

    def _comparison_view(self, row):
        """Copy persisted comparison figures and references, never recompute against the current bill."""
        from ecs_ec.costs.schemas import ComparisonDetail
        return ComparisonDetail.model_validate(view(row) | dict(calculation_id=str(row.calculation_id),
            bill_revision_id=str(row.bill_revision_id), cutoff_at=row.cutoff_at.isoformat())).model_dump(mode='json')

    async def get_comparison(self, principal, comparison_id):
        """Read an authorized historical comparison even if a later bill/calculation has made the current pair pending."""
        from ecs_ec.costs.models import Comparison
        self.authorize(principal)
        async with UnitOfWork(self.database.sessions) as uow:
            row = await uow.session.scalar(select(Comparison).join(Calculation).join(BillingCycle).join(Supply).where(
                Comparison.id == comparison_id, Supply.building_id == self.building_id))
            if row is None:
                raise CostsProblem('comparison_not_found', 404)
            return self._comparison_view(row)

    async def put_supply(self, principal, command, key, *, if_match=None, if_none_match=None):
        """Create/update the singleton using strong preconditions after authorized idempotent replay."""
        from ecs_ec.costs.schemas import SupplyInput
        command = SupplyInput.model_validate(command)
        async def run(uow, actor_ref):
            """Verify actual physicalCAT-01 association and commit current configuration/evidence atomically."""
            if if_match is not None and if_none_match is not None:
                raise CostsProblem('incompatible_preconditions', 422)
            if if_none_match is not None and if_none_match != '*':
                raise CostsProblem('invalid_precondition', 422)
            row = await uow.session.scalar(select(Supply).where(Supply.building_id == self.building_id).with_for_update())
            created = row is None
            if created:
                if if_none_match != '*':
                    if if_match is not None:
                        raise CostsProblem('supply_revision_conflict', 412)
                    raise CostsProblem('revision_required', 428)
            else:
                if if_none_match == '*':
                    raise CostsProblem('supply_exists', 412)
                require_match(if_match, 'supply', row.id, row.revision)
            source = await self.consumption.source_status('CAT-01', cutoff_at=self.clock.now(), unit_of_work=uow)
            if source['source_mode'] != 'measured' or source['source_id'] != command.general_source_id:
                raise CostsProblem('physical_general_required', 422)
            now = self.clock.now()
            if created:
                row = Supply(id=uuid4(), building_id=self.building_id, revision=1, data=command.model_dump(mode='json'),
                    created_at=now, updated_at=now, actor_ref=actor_ref, retain_until=anniversary(now, self.timezone))
                uow.session.add(row)
            else:
                row.data, row.revision, row.updated_at, row.actor_ref = command.model_dump(mode='json'), row.revision + 1, now, actor_ref
                row.retain_until = max(row.retain_until, anniversary(now, self.timezone))
            await uow.session.flush()
            await self.evidence.append(uow, building_id=self.building_id, row=row, action='costs.supply.changed')
            from ecs_ec.costs.schemas import SupplyDetail
            return SupplyDetail.model_validate(view(row)).model_dump(mode='json'), 201 if created else 200
        return await self._mutate(principal, 'costs.configuration.manage', 'supply.put', key, command.model_dump(mode='json'), run)

    async def create_profile(self, principal, command, key):
        """Append a full-calendar revision using the latest saved version, including drafts, as concurrency base."""
        from ecs_ec.costs.profiles import append_profile
        from ecs_ec.costs.schemas import ProfileInput
        command = ProfileInput.model_validate(command)
        async def run(uow, actor_ref):
            """Hold the supply lock while validating chain identity, writing segments and common audit."""
            supply = await uow.session.get(Supply, command.supply_id)
            if supply is None or supply.building_id != self.building_id:
                raise CostsProblem('supply_not_found', 404)
            if command.timezone != self.timezone:
                raise CostsProblem('invalid_timezone', 422)
            row = await append_profile(uow, supply, command, actor_ref, self.clock)
            return self._profile_view(row), 201
        return await self._mutate(principal, 'costs.configuration.manage', 'profile.create', key, command.model_dump(mode='json'), run)

    def _profile_view(self, row):
        """Copy the immutable full profile data and chain metadata, never mix segments from different versions."""
        from ecs_ec.costs.schemas import ProfileDetail
        return ProfileDetail.model_validate(view(row) | dict(previous_version_id=str(row.previous_version_id) if row.previous_version_id else None)).model_dump(mode='json')

    async def profiles(self, principal, *, limit=25, cursor=None):
        """List profile revisions with metadata distinguishing latest saved from selected published at one cutoff."""
        from ecs_ec.costs.models import ProfileVersion
        from ecs_ec.costs.repository import selected_profile, page_rows
        self.authorize(principal, 'costs.configuration.read')
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            supply = await uow.session.scalar(select(Supply).where(Supply.building_id == self.building_id))
            if supply is None:
                return dict(items=[], next_cursor=None, latest_version_id=None, selected_published_version_id=None, latest_version=None, selected_published_version=None, cutoff_at=self.clock.now().isoformat())
            rows, continuation, cutoff = await page_rows(uow, select(ProfileVersion).where(ProfileVersion.supply_id == supply.id), ProfileVersion,
                settings=self.identity.settings, scope='costs.profiles', filters=dict(supply_id=str(supply.id)),
                limit=limit, cursor=cursor, now=self.clock.now())
            latest = await selected_profile(uow, supply.id, cutoff, published=False)
            published = await selected_profile(uow, supply.id, cutoff)
            return dict(items=[self._profile_view(row) for row in rows], next_cursor=continuation, cutoff_at=cutoff.isoformat(),
                latest_version_id=str(latest.id) if latest else None, selected_published_version_id=str(published.id) if published else None,
                latest_version=self._profile_view(latest) if latest else None, selected_published_version=self._profile_view(published) if published else None)

    async def read_snapshot(self, building_id, start, end, cutoff_at, principal, *, unit_of_work=None):
        """Expose the real005 producer while preserving the caller's coherent capture and current authorization."""
        from ecs_ec.costs.snapshots import read_snapshot
        return await read_snapshot(self, building_id, start, end, cutoff_at, principal, unit_of_work=unit_of_work)

    async def history(self, principal, **filters):
        """Read paginated cycle/revision history, including ongoing cycles, without creating or prorating results."""
        return await self.cycles(principal, **filters)


def require_match(value, kind, identifier, revision):
    """Require one strong costs tag, distinguishing missing428, malformed422 and stale412 preconditions."""
    import re
    if value is None:
        raise CostsProblem('revision_required', 428)
    if not re.fullmatch(r'"costs:[a-z]+:[0-9a-f-]{36}:[1-9][0-9]*"', value):
        raise CostsProblem('invalid_precondition', 422)
    if value != f'"costs:{kind}:{identifier}:{revision}"':
        raise CostsProblem('revision_conflict', 412)
