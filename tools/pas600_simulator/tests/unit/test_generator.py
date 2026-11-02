"""Known interval values verify generation without invoking native writers."""
from decimal import Decimal
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.generator import generate_samples


def test_known_energy_and_absent_total():
    """A single 4kWh interval yields 100/104; absent categories yield no samples."""
    raw = SimulationScenario().model_dump(mode='json')
    raw['end'] = '2026-01-01T00:15:00Z'
    raw = SimulationScenario().model_dump(mode='json')
    raw['end'] = '2026-01-01T00:15:00Z'
    raw['categories'] = [c if c['category_id'] == 'CAT-03' else {'category_id': c['category_id'], 'has_meter': False} for c in raw['categories']]
    raw['categories'][2]['expected_range'].update(min='4', max='4')
    samples = list(generate_samples(SimulationScenario.model_validate(raw)))
    assert len(samples) == 1
    assert samples[0].energy == Decimal('4')
    assert samples[0].counter_before == Decimal('100')
    assert samples[0].counter_after == Decimal('104')


def test_absence_zero_total_independence():
    """No meters yields nothing; measured total never sums the other categories."""
    raw = SimulationScenario().model_dump(mode='json')
    raw['end'] = '2026-01-01T00:15:00Z'
    for c in raw['categories']:
        c['expected_range'].update(min='1', max='1')
    raw['categories'][0]['expected_range'].update(min='2', max='2')
    samples = list(generate_samples(SimulationScenario.model_validate(raw)))
    assert len(samples) == 7 and samples[0].energy == 2
    assert sum(s.energy for s in samples[1:]) == 6
    raw['categories'] = [{'category_id': c['category_id'], 'has_meter': False} for c in raw['categories']]
    assert list(generate_samples(SimulationScenario.model_validate(raw))) == []


def test_interval_channel():
    """An evidenced interval descriptor emits N readings without a cumulative reference."""
    from pas600_simulator.generator import readings
    raw = SimulationScenario().model_dump(mode='json')
    raw['end'] = '2026-01-01T00:15:00Z'
    meter = raw['categories'][0]['meter']
    meter.update(semantics='interval', timestamp_role='interval_end')
    meter['provenance'].update(evidence='synthetic test descriptor', sha256='0' * 64)
    scenario = SimulationScenario.model_validate(raw)
    samples = [s for s in generate_samples(scenario) if s.category_id == 'CAT-01']
    assert samples[0].counter_before is None
    assert len(readings(scenario.categories[0].meter, samples)) == 1


def test_order_independence():
    """Category iteration order cannot change sample keys, values or counters."""
    scenario = SimulationScenario()
    first = list(generate_samples(scenario))
    scenario.categories.reverse()
    assert list(generate_samples(scenario)) == first
