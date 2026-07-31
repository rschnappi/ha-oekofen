"""Tests for the Party-/Urlaubsprogramm timestamp conversion helpers (datetime_common.py)."""
from datetime import datetime, timezone

import pytest
from homeassistant.util import dt as dt_util

from custom_components.oekofen.datetime_common import (
    datetime_to_device_seconds,
    device_seconds_to_datetime,
)


@pytest.fixture(autouse=True)
def vienna_timezone():
    """Pin Home Assistant's default timezone so the tests are deterministic."""
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(dt_util.get_time_zone("Europe/Vienna"))
    yield
    dt_util.set_default_time_zone(original)


def test_device_seconds_interpreted_as_local_wallclock_not_utc():
    # The device stores "2026-07-10 18:00:00 local" as if that wall-clock
    # time were itself a UTC timestamp (see datetime_common.py docstring).
    raw = int(datetime(2026, 7, 10, 18, 0, 0, tzinfo=timezone.utc).timestamp())

    result = device_seconds_to_datetime(raw)
    local = dt_util.as_local(result)

    assert (local.year, local.month, local.day, local.hour, local.minute) == (
        2026, 7, 10, 18, 0,
    )


def test_zero_or_negative_raw_value_is_none():
    assert device_seconds_to_datetime(0) is None
    assert device_seconds_to_datetime(-100) is None


def test_invalid_raw_value_is_none():
    assert device_seconds_to_datetime(None) is None
    assert device_seconds_to_datetime("not-a-number") is None


def test_round_trip_preserves_raw_seconds():
    raw = int(datetime(2026, 12, 24, 8, 15, 0, tzinfo=timezone.utc).timestamp())
    dt_value = device_seconds_to_datetime(raw)
    assert datetime_to_device_seconds(dt_value) == raw


def test_round_trip_survives_a_different_source_timezone():
    """A datetime coming in tagged with a different tzinfo should still
    round-trip correctly, since datetime_to_device_seconds normalizes to
    local time first."""
    raw = int(datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    dt_value = device_seconds_to_datetime(raw)

    from datetime import timedelta, timezone as tz
    shifted = dt_value.astimezone(tz(timedelta(hours=5)))

    assert datetime_to_device_seconds(shifted) == raw
