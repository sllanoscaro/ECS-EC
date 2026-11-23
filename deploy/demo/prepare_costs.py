"""Explicit local-demo provisioning; preserve all existing consumption and human accounts."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, text

from demo_profile import channels
from ecs_ec.consumption.catalog_storage import BuildingRow, read_revisions, lock_configuration
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.models import ConfigurationInput
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork

ACTOR = 'process:costs_demo'
MARKER = Path('/acquisition/costs-demo-v1.json')
REFERENCE = 'synthetic:costs-demo-v1'


def tariff(supply_id, timezone, valid_from):
    """Explicit illustrative prices; demand/tax stay unavailable without genuine retained history."""
    def charge(code, kind, unit, price, taxes=()):
        return dict(code=code, kind=kind, quantity_unit=unit, unit_price=price,
            tax_basis='impuesto_separado' if kind == 'impuesto' else 'neto', applicability='always',
            vigency_strategy='exact_intervals' if unit == 'kWh' else 'cycle_once',
            source_refs=[REFERENCE], tax_codes=list(taxes))
    return dict(supply_id=str(supply_id), expected_previous_version_id=None, tariff='BT4.3', currency='CLP',
        publication_state='published', timezone=timezone, source_refs=[REFERENCE],
        territory_conditions='Demostración sintética local, sin validez comercial ni tarifaria.',
        required_kinds=['energia','transmision','fijo','potencia_suministrada','demanda_punta','impuesto'],
        segments=[dict(valid_from=valid_from, valid_to=None, source_refs=[REFERENCE],
            peak_calendar=dict(version='demo-peak-v1', months=[4,5,6,7,8,9], weekdays=[0,1,2,3,4],
                start_time='18:00', end_time='22:00', excluded_dates=[]),
            historical_rule='two_monthly_maxima_12_months_v1',
            billing_month_policy=dict(version='demo-month-v1', mode='documented_rule', source_refs=[REFERENCE], rule_id='cycle_start_month_v1'),
            rounding_policy=dict(precision=50, quantum='1', mode='ROUND_HALF_UP', stage='component'),
            charges=[charge('energy','energia','kWh','100'), charge('transmission','transmision','kWh','8'),
                charge('fixed','fijo','cycle','2000'), charge('supplied','potencia_suministrada','kW','1000'),
                charge('peak','demanda_punta','kW','500'),
                charge('iva','impuesto','CLP','0.19',('energy','transmission','fixed','supplied','peak'))])])


def bill_for(calculation, timezone, now):
    """Build a clearly identified synthetic document with comparable and excluded lines."""
    from ecs_ec.costs.money import number, decimal_text
    lines = []
    net = Decimal(0)
    for component in calculation['components']:
        if component['kind'] == 'impuesto':
            continue
        amount = ((number(component['presented_amount']) * Decimal('0.99')).quantize(Decimal(1), rounding=ROUND_HALF_UP)
            if component['presented_amount'] is not None else Decimal('1500'))
        net += amount
        lines.append(dict(code=component['code'], description='Concepto ilustrativo de demostración',
            quantity=component['basis_value'], unit=component['unit'], amount=decimal_text(amount), tax_basis='neto',
            tax_amount=None, cycle_relation='current_cycle', document_reference=REFERENCE))
    tax = (net * Decimal('0.19')).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    lines.append(dict(code='iva', description='IVA ilustrativo del documento', quantity=decimal_text(net), unit='CLP',
        amount=decimal_text(tax), tax_basis='impuesto_separado', tax_amount=None, cycle_relation='current_cycle', document_reference=REFERENCE))
    request=calculation['snapshot']['request']
    return dict(start=request['start'], end=request['end'], supply_id=calculation['snapshot']['supply_id'],
        external_identifier='DEMO-COSTOS-'+calculation['cycle_id'], issued_at=now.isoformat(), timezone=timezone,
        declared_start=None, declared_end=None, boundary_criterion=REFERENCE, boundary_limited=False,
        document_reference=REFERENCE, currency='CLP', energy_read=next(c['basis_value'] for c in calculation['components'] if c['kind']=='energia'),
        demand_read=None, demand_billed=None, declared_tax=decimal_text(tax), total_payable=decimal_text(net+tax), lines=lines)


async def prepare_financial_demo(database, clock, settings, building_id):
    """Trusted local process orchestrates the existing owners; never impersonates a human session."""
    from ecs_ec.consumption.models import instant
    from ecs_ec.consumption.queries import Consumption
    from ecs_ec.core.retention import anniversary
    from ecs_ec.costs.models import Supply, Calculation, BillingCycle, Bill, BillRevision, Comparison
    from ecs_ec.costs.schemas import SupplyInput, CalculateRequest
    from ecs_ec.costs.profiles import append_profile
    from ecs_ec.costs.repository import selected_profile
    from ecs_ec.costs.services import Costs
    from ecs_ec.costs.snapshots import capture
    from ecs_ec.costs.engine import evaluate
    from ecs_ec.costs.bills import append_bill
    from ecs_ec.identity.settings import IdentitySettings
    from ecs_ec.identity.services import Identity
    identity=Identity(database, IdentitySettings(), clock, settings.building_timezone)
    consumption=Consumption(database, clock, building_id, MeasurementStore())
    service=Costs(database, clock, identity, consumption)
    marker=json.loads(MARKER.read_text())
    async with UnitOfWork(database.sessions) as uow:
        await lock_configuration(uow, building_id)
        now=clock.now()
        supply=await uow.session.scalar(select(Supply).where(Supply.building_id==building_id))
        if supply is None:
            data=SupplyInput(general_board_ref='Suministro general · Demostración local', category_id='CAT-01',
                general_source_id=UUID(channels()[0]['source_id']), distributor='Demostración sintética',
                location='Edificio de demostración sintético', connection_conditions='Condiciones ilustrativas para revisión visual',
                document_refs=[REFERENCE], measurement_point_differences=[])
            supply=Supply(id=uuid4(),building_id=building_id,revision=1,data=data.model_dump(mode='json'),
                created_at=now,updated_at=now,actor_ref=ACTOR,retain_until=anniversary(now,settings.building_timezone))
            uow.session.add(supply)
            await uow.session.flush()
            await service.evidence.append(uow,building_id=building_id,row=supply,action='costs.supply.changed')
        elif REFERENCE not in supply.data.get('document_refs',[]):
            raise RuntimeError('costs_demo_refuses_existing_supply')
        profile=await selected_profile(uow,supply.id,now,published=False)
        if profile is None:
            profile=await append_profile(uow,supply,tariff(supply.id,settings.building_timezone,marker['effective_from']),ACTOR,clock)
        elif REFERENCE not in profile.data.get('source_refs',[]) or profile.publication_state!='published':
            raise RuntimeError('costs_demo_refuses_existing_profile')
        # Publish owned configuration first; the financial capture below uses a separate read-only transaction.
        await uow.commit()
        await lock_configuration(uow,building_id)
        now=clock.now()
        # A previous explicit demo cycle survives reruns; no recalculation or duplicate document.
        cycle=await uow.session.scalar(select(BillingCycle).where(BillingCycle.supply_id==supply.id,
            BillingCycle.data['boundary_criterion'].astext==REFERENCE).order_by(BillingCycle.created_at).limit(1))
        existing=await uow.session.scalar(select(Calculation).where(Calculation.cycle_id==cycle.id).order_by(Calculation.revision.desc()).limit(1)) if cycle else None
        if existing:
            if existing.actor_ref!=ACTOR:
                raise RuntimeError('costs_demo_calculation_changed_by_administrator')
            calculation=await service._calculation_view(uow,existing)
            request=calculation['snapshot']['request']
            async with UnitOfWork(database.sessions) as read:
                await read.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                consumption_capture=await consumption.read_report_snapshot(building_id,instant(request['start']),instant(request['end']),
                    'detail',now,None,unit_of_work=read)
        else:
            async with UnitOfWork(database.sessions) as read:
                await read.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                snapshot=await consumption.read_general_snapshot(building_id,instant(marker['effective_from']),now,now,read)
                rows=sorted(snapshot.rows,key=lambda r:r.start)
                if not rows:
                    print(json.dumps(dict(status='waiting_for_physical_interval',configuration_revision=marker['configuration_revision'])),flush=True)
                    return
                consecutive=[rows[0]]
                for row in rows[1:]:
                    if row.start!=consecutive[-1].end:break
                    consecutive.append(row)
                request=CalculateRequest(start=consecutive[0].start,end=consecutive[-1].end,supply_id=supply.id,
                    timezone=settings.building_timezone,boundary_criterion=REFERENCE)
                inputs=await capture(read,consumption=consumption,supply_id=supply.id,request=request,cutoff_at=now)
                consumption_capture=await consumption.read_report_snapshot(building_id,request.start,request.end,
                    'detail',now,None,unit_of_work=read)
            if inputs.profile is None or REFERENCE not in inputs.profile.source_refs or REFERENCE not in inputs.supply.document_refs:
                raise RuntimeError('costs_demo_configuration_changed')
            result=evaluate(inputs)
            if not any(c['kind']=='energia' and c['presented_amount'] is not None for c in result['components']):
                raise RuntimeError('costs_demo_energy_not_calculable')
            calculation=await service._save_calculation(uow,ACTOR,inputs,result)
            existing=await uow.session.get(Calculation,UUID(calculation['id']))
        external='demo-costos-'+calculation['cycle_id']
        bill=await uow.session.scalar(select(BillRevision).join(Bill).where(Bill.supply_id==supply.id,
            Bill.external_identifier_normalized==external).order_by(BillRevision.revision.desc()).limit(1))
        if bill is None:
            bill,_=await append_bill(uow,supply,bill_for(calculation,settings.building_timezone,now),ACTOR,clock)
            await service.evidence.append(uow,building_id=building_id,row=bill,action='costs.bill.created')
        comparison=await uow.session.scalar(select(Comparison).where(Comparison.calculation_id==existing.id,Comparison.bill_revision_id==bill.id))
        if comparison is None:
            await service._save_comparison(uow,existing,bill,ACTOR)
        now=clock.now()
        from ecs_ec.costs.history import cycle_view
        from ecs_ec.costs.distribution import project_distribution
        distribution=project_distribution(calculation,consumption_capture)
        if distribution['state']!='available':
            raise RuntimeError('costs_demo_distribution_not_available:'+str(distribution['reason_code']))
        cycle=await uow.session.get(BillingCycle,UUID(calculation['cycle_id']))
        preview=dict(cycle=(await cycle_view(service,uow,cycle,now)).model_dump(mode='json'),
            distribution=distribution,bill=service._bill_view(bill))
        await uow.commit()
    marker.update(calculation_id=calculation['id'],cycle_id=calculation['cycle_id'])
    temporary=MARKER.with_name(MARKER.name+'.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(marker));temporary.chmod(0o600);temporary.replace(MARKER)
    print(json.dumps(dict(status='ready',calculation_id=calculation['id'],sufficiency=calculation['sufficiency'],demo=True)),flush=True)
    return preview


async def configure(database, clock, settings, building_id):
    """Switch only the demo general source prospectively, using001's normal revision/evidence path."""
    async with UnitOfWork(database.sessions) as uow:
        building = await uow.session.get(BuildingRow, building_id)
        if building is None or building.name != 'Edificio de demostración sintético' or building.timezone != settings.building_timezone:
            raise RuntimeError('costs_demo_refuses_existing_installation')
        from ecs_ec.costs.models import Supply
        from ecs_ec.costs.repository import selected_profile
        supply=await uow.session.scalar(select(Supply).where(Supply.building_id==building_id))
        if supply and REFERENCE not in supply.data.get('document_refs',[]):
            raise RuntimeError('costs_demo_refuses_existing_supply')
        profile=await selected_profile(uow,supply.id,clock.now(),published=False) if supply else None
        if profile and (REFERENCE not in profile.data.get('source_refs',[]) or profile.publication_state!='published'):
            raise RuntimeError('costs_demo_refuses_existing_profile')
        previous = (await read_revisions(uow, building_id))[-1]
        expected = {c['category_id']: UUID(c['source_id']) for c in channels()}
        if any(c.has_meter and c.source_id != expected[c.category_id] for c in previous.categories):
            raise RuntimeError('costs_demo_refuses_external_sources')
        general = previous.entry('CAT-01')
        if not general.has_meter or not MARKER.exists():
            if MARKER.exists():
                raise RuntimeError('costs_demo_source_changed_after_preparation')
            entries = [c.model_dump(exclude={'category_revision'}) for c in previous.categories]
            entries[0].update(has_meter=True, source_id=expected['CAT-01'], source_label='Demo CAT-01 · Costos')
            previous = await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=building_id,
                request=ConfigurationInput(expected_revision=previous.revision, effective_from=None,
                    timezone=building.timezone, categories=entries), actor_ref=ACTOR)
            await uow.commit()
        return dict(configuration_revision=previous.revision, effective_from=previous.effective_from.isoformat())


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure-only', action='store_true')
    parser.add_argument('--export-preview', type=Path, help='Save real local-demo responses for visual verification; never session data')
    args = parser.parse_args()
    settings = Settings()
    if settings.environment != 'local' or not settings.demo_calendar:
        raise RuntimeError('costs_demo_requires_local_calendar')
    database, clock = Database(settings.database_url.get_secret_value()), SystemClock()
    try:
        building_id = UUID(os.environ['IDENTITY_BUILDING_ID'])
        configured = await configure(database, clock, settings, building_id)
        if not MARKER.exists():
            MARKER.write_text(json.dumps(configured))
            MARKER.chmod(0o600)
        print(json.dumps(dict(status='configured', **configured)), flush=True)
        if not args.configure_only:
            preview=await prepare_financial_demo(database, clock, settings, building_id)
            if preview is not None and args.export_preview:
                args.export_preview.write_text(json.dumps(preview))
                args.export_preview.chmod(0o600)
    finally:
        await database.close()


if __name__ == '__main__':
    asyncio.run(main())
