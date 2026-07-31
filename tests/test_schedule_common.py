"""Tests for the shared weekly-schedule helpers (schedule_common.py)."""
from datetime import time as dt_time

from custom_components.oekofen.schedule_common import (
    BLOCKS_PER_DAY,
    build_schedule_slots,
    seconds_to_time,
    time_to_seconds,
)


def test_build_schedule_slots_shape_for_one_circuit():
    slots = build_schedule_slots({"hk": [0], "ww": [], "zirkp": []})

    # 1 circuit * 2 programs * 7 days
    assert len(slots) == 14
    first = slots[0]
    assert first["circuit_type"] == "hk"
    assert first["circuit_index"] == 0
    assert first["program"] == 0
    assert first["day"] == 0
    assert first["base"] == "CAPPL:LOCAL.hk[0].zeitprogramm[0].tag[0]"
    assert first["key"] == "hk0_zeit1_So"
    assert first["label"] == "Heizkreis 1 Zeit 1 Sonntag"


def test_build_schedule_slots_device_weekday_order_is_sunday_first():
    """Regression check for the device's confirmed non-standard weekday indexing."""
    slots = build_schedule_slots({"hk": [0], "ww": [], "zirkp": []})
    day0, day1, day6 = slots[0], slots[1], slots[6]
    assert "Sonntag" in day0["label"]
    assert "Montag" in day1["label"]
    assert "Samstag" in day6["label"]


def test_build_schedule_slots_counts_multiple_circuit_types():
    slots = build_schedule_slots({"hk": [0, 1], "ww": [0], "zirkp": [0]})
    assert len(slots) == (2 + 1 + 1) * 2 * 7


def test_build_schedule_slots_empty_circuits_gives_no_slots():
    assert build_schedule_slots({"hk": [], "ww": [], "zirkp": []}) == []


def test_seconds_to_time_basic_values():
    assert seconds_to_time(0) == dt_time(0, 0, 0)
    assert seconds_to_time(3661) == dt_time(1, 1, 1)
    assert seconds_to_time("64800") == dt_time(18, 0, 0)


def test_seconds_to_time_clamps_out_of_range():
    assert seconds_to_time(-5) == dt_time(0, 0, 0)
    assert seconds_to_time(999999) == dt_time(23, 59, 59)


def test_seconds_to_time_invalid_input_returns_none():
    assert seconds_to_time(None) is None
    assert seconds_to_time("not-a-number") is None


def test_time_to_seconds_matches_expected_value():
    assert time_to_seconds(dt_time(18, 30, 15)) == 18 * 3600 + 30 * 60 + 15


def test_seconds_and_time_round_trip():
    original = dt_time(7, 45, 0)
    assert seconds_to_time(time_to_seconds(original)) == original


def test_blocks_per_day_is_three():
    assert BLOCKS_PER_DAY == 3
