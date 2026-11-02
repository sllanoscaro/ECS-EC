"""Known calendar/quantum cases independent of generation and backend."""
from datetime import datetime
from decimal import Decimal
import pytest
from pas600_simulator.calendar import interval_count, quantum_bounds


def test_dst_and_non_divisible():
    """Fall-back repeated hour counts twice; partial samples are rejected."""
    assert interval_count(datetime.fromisoformat('2026-11-01T00:00:00-04:00'), datetime.fromisoformat('2026-11-01T03:00:00-05:00'), 'America/New_York', 15) == 16
    with pytest.raises(ValueError):
        interval_count(datetime.fromisoformat('2026-01-01T00:00:00Z'), datetime.fromisoformat('2026-01-01T00:16:00Z'), 'Etc/UTC', 15)
    with pytest.raises(ValueError):
        interval_count(datetime(2026, 1, 1), datetime(2026, 1, 2), 'Etc/UTC', 15)


@pytest.mark.parametrize('low,high,q', [('NaN','1','1'), ('0','Infinity','1'), ('0','1','0'), ('0.1','0.2','1'), ('-1','1','1')])
def test_invalid_quantum(low, high, q):
    """Reject nonfinite, negative, empty-grid and nonpositive quantum ranges."""
    with pytest.raises(ValueError):
        quantum_bounds(Decimal(low), Decimal(high), Decimal(q))
