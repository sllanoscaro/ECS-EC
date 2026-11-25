"""008 pinned real-zone expectations distinguish nominal scheduling from protected retention anniversaries."""

from datetime import UTC, datetime

from ecs_ec.notifications.calendar import next_occurrences


def daily(time="06:00", **options):
    """Build one documented local schedule anchored before all reference cuts."""
    return dict(
        kind="diaria", starts_at="2025-01-01T00:00:00Z", local_time=time, **options
    )


def test_daily_and_elapsed_intervals_are_different_across_dst():
    """Santiago midnight jump yields23h between06:00 slots; elapsed24h preserves UTC instead."""
    after = datetime(2026, 9, 5, 12, tzinfo=UTC)
    dates = next_occurrences(daily(), "America/Santiago", after, 3)
    assert [d["resolved_at"] for d in dates] == [
        "2026-09-06T09:00:00Z",
        "2026-09-07T09:00:00Z",
        "2026-09-08T09:00:00Z",
    ]
    assert dates[0]["window"] == {
        "start": "2026-09-05T10:00:00Z",
        "end": "2026-09-06T09:00:00Z",
    }


def test_first_valid_instant_is_not_requested_time_plus_gap():
    """Nonexistent00:30 becomes01:00, the first valid instant, rather than01:30."""
    result = next_occurrences(
        daily("00:30"), "America/Santiago", datetime(2026, 9, 5, 12, tzinfo=UTC), 1
    )[0]
    assert result["resolved_at"] == "2026-09-06T04:00:00Z"
    assert result["calendar_adjustment"] == "hora_inexistente"


def test_fold_uses_first_occurrence():
    """Santiago23:30 repeated on April4 maps to02:30Z, never a second email at03:30Z."""
    result = next_occurrences(
        daily("23:30"), "America/Santiago", datetime(2026, 4, 4, 12, tzinfo=UTC), 1
    )[0]
    assert result["resolved_at"] == "2026-04-05T02:30:00Z"
    assert result["calendar_adjustment"] == "primera_hora_repetida"


def test_nominal_31_survives_february():
    """Monthly anchor31 clamps February only and returns to31 in March."""
    schedule = daily()
    schedule.update(kind="mensual", day_of_month=31)
    result = next_occurrences(schedule, "Etc/UTC", datetime(2026, 1, 30, tzinfo=UTC), 3)
    assert [r["resolved_at"] for r in result] == [
        "2026-01-31T06:00:00Z",
        "2026-02-28T06:00:00Z",
        "2026-03-31T06:00:00Z",
    ]


def test_annual_leap_anchor_returns():
    """February29 resolves to28 in2027 but returns to29 in2028 without rewriting its nominal day."""
    schedule = daily()
    schedule.update(kind="anual", month=2, day_of_month=29)
    result = next_occurrences(schedule, "Etc/UTC", datetime(2026, 3, 1, tzinfo=UTC), 2)
    assert [r["resolved_at"] for r in result] == [
        "2027-02-28T06:00:00Z",
        "2028-02-29T06:00:00Z",
    ]


def test_interval_is_strictly_after_activation_and_retains_anchor():
    """An activation at00:30 yields01:00 rather than replaying00:00/00:30."""
    schedule = dict(
        kind="intervalo",
        starts_at="2026-01-01T00:00:00Z",
        interval_value=30,
        interval_unit="minutos",
    )
    result = next_occurrences(
        schedule, "America/Santiago", datetime(2026, 1, 1, 0, 30, tzinfo=UTC), 1
    )[0]
    assert result["resolved_at"] == "2026-01-01T01:00:00Z"
    assert result["window"] == {
        "start": "2026-01-01T00:30:00Z",
        "end": "2026-01-01T01:00:00Z",
    }


def test_user_approved_initial_cut_can_be_explicitly_empty():
    """Preserve starts_at when it is the first due instant; no invented observation period precedes it."""
    schedule = dict(
        kind="intervalo",
        starts_at="2026-01-01T01:00:00Z",
        interval_value=30,
        interval_unit="minutos",
    )
    result = next_occurrences(schedule, "Etc/UTC", datetime(2026, 1, 1, tzinfo=UTC), 2)
    assert result[0]["window"] == {
        "start": "2026-01-01T01:00:00Z",
        "end": "2026-01-01T01:00:00Z",
    }
    assert result[0]["initial_window_empty"] is True
    assert result[1]["initial_window_empty"] is False
