"""Persist complete, incomplete and unknown coverage without manufacturing zero counts."""

from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from ecs_ec.audit.models import CoverageRecord
from ecs_ec.audit.services import CoverageInput, CoverageService
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


def coverage(clock, **changes):
    """Return complete zero-event evidence for one explicit window, overridable for edge cases."""
    start, end = clock.now(), clock.now() + timedelta(hours=1)
    data = dict(content_type="synthetic", source_ref="process:synthetic", source_revision="cursor:1",
                cutoff_at=end, window_start=start, window_end=end, integrity="completa",
                observed_count=0, covered_periods=[{"start": start, "end": end}], known_gaps=[],
                recorded_by="process:synthetic")
    return CoverageInput(**(data | changes))


async def test_coverage_states_persist(database, clock):
    """Complete zero is distinct from observed partial counts and unavailable history."""
    start, end = clock.now(), clock.now() + timedelta(hours=1)
    middle = start + timedelta(minutes=30)
    complete = coverage(clock)
    partial = coverage(clock, integrity="incompleta", observed_count=3,
                       covered_periods=[{"start": middle, "end": end}],
                       known_gaps=[{"start": start, "end": middle}], limitation_code="before_recording")
    unknown = coverage(clock, integrity="desconocida", observed_count=None, covered_periods=[],
                       limitation_code="source_unavailable")
    service = CoverageService(clock, "UTC")
    async with UnitOfWork(database.sessions) as uow:
        rows = [await service.append(uow, value) for value in (complete, partial, unknown)]
        ids = [row.id for row in rows]
        await uow.commit()
    async with UnitOfWork(database.sessions) as uow:
        saved = {row.id: row for row in (await uow.session.scalars(select(CoverageRecord).where(
            CoverageRecord.id.in_(ids)))).all()}
        assert [saved[i].observed_count for i in ids] == [0, 3, None]
        assert saved[ids[1]].known_gaps[0]["end"] == middle.isoformat().replace("+00:00", "Z")
        assert saved[ids[2]].source_revision == "cursor:1"
        assert all(saved[i].retain_until > saved[i].created_at for i in ids)


@pytest.mark.parametrize("changes", [
    {"observed_count": -1}, {"observed_count": None}, {"covered_periods": []},
    {"window_end": "2025-12-31T00:00:00Z"},
    {"covered_periods": [{"start": "2025-12-31T00:00:00Z", "end": "2026-01-01T01:00:00Z"}]},
    {"integrity": "incompleta", "known_gaps": []},
    {"known_gaps": [{"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}]},
    {"covered_periods": [{"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:45:00Z"},
                         {"start": "2026-01-01T00:30:00Z", "end": "2026-01-01T01:00:00Z"}]},
])
async def test_reject_invalid_coverage(clock, changes):
    """Reject impossible window/count/integrity claims and overlapping or out-of-window periods."""
    with pytest.raises(ValidationError):
        coverage(clock, **changes)
