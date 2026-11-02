"""Exact independent anomaly denominators and disjoint deterministic positions."""
from decimal import Decimal
from pas600_simulator.anomalies import select_positions
from pas600_simulator.scenario import AnomalyRates


def test_ten_ten_ten():
    """100 original intervals assign 10+10+10, leaving exactly70 normal positions."""
    rates = AnomalyRates(missing='10', format='10', out_of_range='10')
    result = select_positions('seed', 'CAT-03', 100, rates)
    assert len(result) == 30
    assert all(list(result.values()).count(kind) == 10 for kind in ('missing', 'format', 'out_of_range'))
    assert select_positions('seed', 'CAT-03', 100, rates) == result
    assert select_positions('seed', 'CAT-05', 100, rates) != result


def test_floor_and_extremes():
    """Counts floor the original N; zero/100% never touch an initial reference."""
    assert select_positions('seed', 'CAT-03', 9, AnomalyRates(missing='10')) == {}
    assert len(select_positions('seed', 'CAT-03', 9, AnomalyRates(missing='100'))) == 9
    assert not select_positions('seed', 'CAT-03', 9, AnomalyRates())


def test_explicit_reserved_and_invalid():
    """Explicit later-class positions cannot be stolen by an earlier random selection."""
    import pytest
    rates = AnomalyRates(missing='10', format='10', positions={'format': list(range(10))})
    selected = select_positions('seed', 'CAT-03', 100, rates)
    assert all(selected[i] == 'format' for i in range(10))
    with pytest.raises(ValueError):
        select_positions('seed', 'CAT-03', 100, AnomalyRates(missing='10', positions={'missing': [0]}))


def test_fractional_and_invalid_rates():
    """Fractional percentages floor exactly and a sum above100 is rejected."""
    import pytest
    assert len(select_positions('seed', 'CAT-03', 100, AnomalyRates(missing='10.99'))) == 10
    with pytest.raises(ValueError):
        AnomalyRates(missing='50.01', format='50')
    with pytest.raises(ValueError):
        select_positions('seed', 'CAT-03', 100, AnomalyRates(missing='10', format='10', positions={'missing': list(range(10)), 'format': list(range(10))}))
