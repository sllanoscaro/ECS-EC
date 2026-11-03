"""Exact adjacency rules for cumulative native energy; no gap interpolation or consumption before reference."""
from datetime import timedelta
from decimal import localcontext


def adjacent_delta(first_at,first_value,last_at,last_value,sampling_minutes):
    """Return exact energy/reason for two valid endpoints; equal counters are a covered zero interval."""
    if last_at-first_at!=timedelta(minutes=sampling_minutes):return None,'gap'
    if last_value<first_value:return None,'counter_decreased'
    with localcontext() as context:
        context.prec=max(50,len(first_value.as_tuple().digits)+len(last_value.as_tuple().digits)+10)
        return last_value-first_value,'candidate'
