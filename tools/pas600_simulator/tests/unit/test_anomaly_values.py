"""Counter anomalies alter increments without creating unintended neighboring outliers."""
from decimal import Decimal
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.generator import generate_samples, readings
from pas600_simulator.anomalies import alter_sample


def test_shift_and_missing():
    """A >10 outlier shifts following counters; a missing endpoint is truly absent."""
    scenario = SimulationScenario(end='2026-01-01T00:45:00Z')
    category = scenario.categories[0]
    original = [s for s in generate_samples(scenario) if s.category_id == 'CAT-01']
    first, shift = alter_sample(original[0], category, 'out_of_range', Decimal(0))
    second, shift = alter_sample(original[1], category, None, shift)
    assert first.energy > 10
    assert second.counter_after - first.counter_after == original[1].energy
    missing, shift = alter_sample(original[2], category, 'missing', shift)
    actual = readings(category.meter, [first, second, missing])
    assert len(actual) == 3
    assert actual[0][1] == Decimal(100)


def test_lower_and_format_dates(tmp_path):
    """Lower outlier is below minimum; date defects preserve their intended values."""
    import json
    from pas600_simulator.report import generate_run
    scenario = SimulationScenario(end='2026-01-01T00:15:00Z', format='json')
    category = scenario.categories[0]
    category.rates.out_of_range_direction = 'below'
    original = next(generate_samples(scenario))
    altered, _ = alter_sample(original, category, 'out_of_range', Decimal(0))
    assert altered.energy == Decimal('-0.001')
    category.rates.format = Decimal(100)
    category.rates.format_mode = 'date'
    manifest = generate_run(scenario, tmp_path / 'run')
    publication = manifest['publications'][0]
    data = json.loads((tmp_path / 'run/data' / publication['key'] / publication['files'][0]['name']).read_text())
    series = data['message']['content']['data']['timeseries'][0]
    assert series['records'][0]['t'] == 0
    assert series['records'][1]['t'] == 'invalid-date'
    assert len((tmp_path / 'run/control/anomalies.jsonl').read_text().splitlines()) == 1


def test_exact_counts_and_unselected_channels(tmp_path):
    """100 samples produce 10/10/10/70 in both formats; other categories stay normal."""
    import json
    from pas600_simulator.report import generate_run
    scenario = SimulationScenario(end='2026-01-02T01:00:00Z')
    category = scenario.categories[2]
    category.rates.missing = Decimal(10)
    category.rates.format = Decimal(10)
    category.rates.out_of_range = Decimal(10)
    for kind in ('csv', 'json'):
        scenario.format = kind
        result = generate_run(scenario, tmp_path / kind)
        assert result['counts']['CAT-03']['assignments'] == {'missing': 10, 'format': 10, 'out_of_range': 10}
        assert result['counts']['CAT-01']['assignments'] == {'missing': 0, 'format': 0, 'out_of_range': 0}
        changes = [json.loads(line) for line in (tmp_path / kind / 'control/anomalies.jsonl').read_text().splitlines()]
        assert len(changes) == 30 and len({r['index'] for r in changes}) == 30
        assert len((tmp_path / kind / 'control/expected.jsonl').read_text().splitlines()) == 700


def test_unrepresentable_outlier_has_no_effects(tmp_path):
    """A below-range increment that would make counters negative fails before output."""
    import pytest
    from pas600_simulator.report import generate_run
    scenario = SimulationScenario(end='2026-01-01T00:15:00Z')
    category = scenario.categories[0]
    category.meter.initial_counter = Decimal(0)
    category.rates.out_of_range = Decimal(100)
    category.rates.out_of_range_direction = 'below'
    with pytest.raises(ValueError):
        generate_run(scenario, tmp_path / 'invalid')
    assert not (tmp_path / 'invalid').exists()


def test_generation_zero_and_full_rates(tmp_path):
    """Both formats preserve exact0/100% assignments for every anomaly class."""
    from pas600_simulator.report import generate_run
    for kind in ('csv', 'json'):
        for anomaly in ('missing', 'format', 'out_of_range'):
            scenario = SimulationScenario(end='2026-01-01T00:45:00Z', format=kind)
            setattr(scenario.categories[0].rates, anomaly, Decimal(100))
            result = generate_run(scenario, tmp_path / f'{kind}-{anomaly}')
            counts = result['counts']['CAT-01']['assignments']
            assert counts[anomaly] == 3 and sum(counts.values()) == 3
            assert all(sum(result['counts'][f'CAT-0{i}']['assignments'].values()) == 0 for i in range(2,8))
