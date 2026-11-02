"""Closed004 tariff rule catalog and immutable full-calendar validation/selection helpers."""

from ecs_ec.costs.schemas import ProfileInput

ENERGY_KINDS = frozenset({'energia', 'transmision', 'servicio_publico'})
SUPPORTED_STRATEGIES = frozenset({'exact_intervals', 'cycle_once'})
SUPPORTED_MONTH_RULES = frozenset({'cycle_end_month_v1', 'cycle_start_month_v1'})


def validate_profile(value):
    """Validate calendar structure and types; unknown business rules remain explicit calculation limitations."""
    return ProfileInput.model_validate(value)


def applicable_segments(profile, start, end):
    """Return intersecting segments from one revision only, in validity order; retain gaps for sufficiency checks."""
    return tuple(sorted((s for s in profile.segments if s.valid_from < end and (s.valid_to is None or s.valid_to > start)), key=lambda s: s.valid_from))


async def append_profile(uow, supply, command, actor_ref, clock):
    """Append a validated complete calendar under the supply lock; expected prior includes saved drafts."""
    from uuid import uuid4
    from sqlalchemy import select
    from ecs_ec.costs.models import Supply, ProfileVersion, ProfileSegment as SegmentRow, ProfileCharge
    from ecs_ec.costs.repository import selected_profile, CostsProblem
    from ecs_ec.costs.adapters import Evidence
    from ecs_ec.costs.money import number
    from ecs_ec.core.retention import anniversary
    command = validate_profile(command)
    supply = await uow.session.scalar(select(Supply).where(Supply.id == supply.id).with_for_update())
    previous = await selected_profile(uow, supply.id, clock.now(), published=False)
    if command.expected_previous_version_id != (previous.id if previous else None):
        raise CostsProblem('profile_revision_conflict')
    if command.supply_id != supply.id:
        raise CostsProblem('supply_mismatch', 422)
    now = clock.now()
    retained = dict(created_at=now, actor_ref=actor_ref, retain_until=anniversary(now, command.timezone))
    profile = ProfileVersion(id=uuid4(), supply_id=supply.id, revision=previous.revision + 1 if previous else 1,
        previous_version_id=previous.id if previous else None, publication_state=command.publication_state,
        data=command.model_dump(mode='json'), **retained)
    uow.session.add(profile)
    await uow.session.flush()
    for segment in command.segments:
        row = SegmentRow(id=uuid4(), profile_version_id=profile.id, valid_from=segment.valid_from,
            valid_to=segment.valid_to, data=segment.model_dump(mode='json'), **retained)
        uow.session.add(row)
        await uow.session.flush()
        for charge in segment.charges:
            uow.session.add(ProfileCharge(id=uuid4(), segment_id=row.id, code=charge.code,
                unit_price=number(charge.unit_price) if charge.unit_price is not None else None,
                data=charge.model_dump(mode='json'), **retained))
    await uow.session.flush()
    await Evidence(clock, command.timezone).append(uow, building_id=supply.building_id, row=profile, action='costs.profile.created')
    return profile
