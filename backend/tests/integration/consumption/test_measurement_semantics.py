"""Acceptance scenarios against a real002 reception harness, deliberately pending its provider.

Spec002 must supply fixture `consumption_reception_environment` with async `publish(records)`
(using Reception.accept and002 UoWs), `rows(category)` (incorporated read), `configure`,
`update_state(category)`, `events()` and `advance(seconds)` (injected clock). Initial
setup uses buildingUUID99, CAT-03/05 with sourceUUID3/5 and a historical revision.
Skips are dependency gaps, never successful acceptance.
"""

import asyncio

import pytest

from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


@pytest.fixture
def reception_environment(request):
    """Use002's real provider harness when registered; never substitute a fake reception/store."""
    try: return request.getfixturevalue("consumption_reception_environment")
    except pytest.FixtureLookupError: pytest.skip("spec-002 reception/storage provider is not implemented")


async def test_equivalence_conflict_overlap_and_contiguity(reception_environment):
    """First original persists; equal kWh duplicates, conflicts/overlaps reject, contiguous history accepts."""
    env = reception_environment
    results = await env.publish([record(value="1000", unit="Wh"), record(), record(value="2"),
        record(start="2026-01-01T00:30:00Z", end="2026-01-01T01:30:00Z"),
        record(start="2026-01-01T01:00:00Z", end="2026-01-01T02:00:00Z")])
    assert [r.status for r in results] == ["accepted", "duplicate", "rejected", "rejected", "accepted"]
    assert results[0].measurement_id == results[1].measurement_id
    rows = await env.rows("CAT-05")
    assert len(rows) == 2 and rows[0].original_value_text == "1000"


async def test_mixed_out_of_order_and_concurrent_admission(reception_environment):
    """Independent valid records survive invalid neighbors; concurrent duplicate has one durable winner."""
    env = reception_environment
    results = await env.publish([record(value="NaN"), record(start="2026-01-01T01:00:00Z", end="2026-01-01T02:00:00Z"), record()])
    assert [r.status for r in results] == ["rejected", "accepted", "accepted"]
    env.advance(900)
    fresh = record(start="2026-01-02T00:00:00Z", end="2026-01-02T01:00:00Z")
    a,b = await asyncio.gather(env.publish([fresh]), env.publish([fresh]))
    assert sorted([a[0].status,b[0].status]) == ["accepted", "duplicate"]
    assert a[0].measurement_id == b[0].measurement_id


async def test_global_and_own_reconfiguration_and_numeric_bounds(reception_environment):
    """The real provider resolves historical source revisions and applies001's unit-invariant bounds."""
    env = reception_environment
    await env.configure("CAT-03", effective_from="2026-01-01T00:30:00Z")
    result = (await env.publish([record()]))[0]
    assert result.status == "accepted" and result.category_revision == 1
    await env.configure("CAT-05", effective_from="2026-01-02T00:30:00Z")
    own = record(start="2026-01-02T00:00:00Z",end="2026-01-02T01:00:00Z")
    assert (await env.publish([own]))[0].reason_code == "source_configuration_changed"
    for unit,value in (("Wh","1e33"),("kWh","1e30"),("MWh","1e27")):
        assert (await env.publish([record(unit=unit,value=value)]))[0].reason_code == "energy_out_of_supported_range"


async def test_duplicate_rejection_keeps_first_acceptance_and_events(reception_environment):
    """Duplicate/rejection preserves original references, accepted clock and accepted_new_data events."""
    env = reception_environment
    accepted = (await env.publish([record(value="1000",unit="Wh")]))[0]
    before = await env.update_state("CAT-05")
    events_before = [e.id for e in await env.events() if e.event_type == "consumption.accepted"]
    env.advance(899)
    results = await env.publish([record(), record(value="2"), record(value="NaN")])
    assert [r.status for r in results] == ["duplicate", "rejected", "rejected"]
    assert results[0].measurement_id == accepted.measurement_id
    after = await env.update_state("CAT-05")
    assert after.last_new_data_at == before.last_new_data_at
    assert after.next_admissible_at == before.next_admissible_at
    assert [e.id for e in await env.events() if e.event_type == "consumption.accepted"] == events_before
    assert (await env.rows("CAT-05"))[0].original_value_text == "1000"


async def test_historical_overlap_across_successive_sources(reception_environment):
    """The category exclusion survives source replacement; a new source cannot overwrite old history."""
    env = reception_environment
    original = (await env.publish([record()]))[0]
    # The legitimate switch occurs at the accepted interval's end. A late record
    # spanning that switch must fail001 before002 can consider any overwrite.
    await env.configure("CAT-05",effective_from="2026-01-01T01:00:00Z")
    crossing = record(start="2026-01-01T00:30:00Z",end="2026-01-01T01:30:00Z")
    assert (await env.publish([crossing]))[0].reason_code == "source_configuration_changed"
    assert (await env.rows("CAT-05"))[0].record_id == original.measurement_id
