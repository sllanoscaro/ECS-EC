"""Strict scenario rules: no hidden meters, duplicate identity or unbounded decimals."""
import pytest
from pas600_simulator.scenario import SimulationScenario


def test_defaults_and_strict_fields():
    """The default is seven independent measured categories, with no anomalies."""
    scenario = SimulationScenario()
    assert len(scenario.categories) == 7
    assert all(c.has_meter for c in scenario.categories)
    with pytest.raises(ValueError):
        SimulationScenario(unknown=True)


def test_category_and_meter_uniqueness():
    """All seven states exist once and measured devices have distinct native IDs."""
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'][1]['meter']['device_local_id'] = raw['categories'][0]['meter']['device_local_id']
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'].pop()
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)


def test_absence_and_decimal_rejection():
    """An absent category has no range/channel/rates; NaN is never a reading."""
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'][0]['has_meter'] = False
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)
    raw['categories'][0] = {'category_id': 'CAT-01', 'has_meter': False}
    assert SimulationScenario.model_validate(raw).categories[0].meter is None
    raw['categories'][1]['expected_range']['max'] = 'NaN'
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)


@pytest.mark.parametrize('changes', [
    {'timezone': 'Does/NotExist'}, {'start': '2026-01-01T00:00:00'},
    {'start': '2026-01-01T00:00:00-03:00'},
    {'end': '2026-01-01T00:16:00Z'},
    {'publication_time': '2026-01-01T00:00:00'},
])
def test_invalid_calendar(changes):
    """All calendar failures are configuration errors, including unknown IANA zones."""
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(changes)


def test_float_and_noninitial_descriptor():
    """Require decimal strings and evidence for interval or noninitial sampling."""
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'][0]['expected_range']['max'] = 0.1
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'][0]['meter'].update(semantics='interval', timestamp_role='interval_end')
    with pytest.raises(ValueError):
        SimulationScenario.model_validate(raw)
