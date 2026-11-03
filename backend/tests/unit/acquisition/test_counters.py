"""Known counter pairs test adjacency, zero, resets and missing evidence without serializing native files."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal


def test_adjacent_zero_gap_and_decrease():
    """Only adjacent compatible valid100→104 creates4; equality is zero and gaps/reset never create energy."""
    from ecs_ec.acquisition.counters import adjacent_delta
    at=datetime(2026,1,1,tzinfo=UTC)
    assert adjacent_delta(at,Decimal(100),at+timedelta(minutes=15),Decimal(104),15)==(Decimal(4),'candidate')
    assert adjacent_delta(at,Decimal(100),at+timedelta(minutes=15),Decimal(100),15)==(Decimal(0),'candidate')
    assert adjacent_delta(at,Decimal(100),at+timedelta(minutes=30),Decimal(104),15)==(None,'gap')
    assert adjacent_delta(at,Decimal(104),at+timedelta(minutes=15),Decimal(100),15)==(None,'counter_decreased')
