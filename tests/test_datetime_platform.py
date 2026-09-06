"""Tests for the datetime platform (datetime.py) - Party-/Urlaubsprogramm fields."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.oekofen.datetime import (
    OekofenDateTime,
    build_datetime_definitions,
)
from custom_components.oekofen.datetime_common import datetime_to_device_seconds

from .conftest import FakeCoordinator, make_point


@pytest.fixture(autouse=True)
def vienna_timezone():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(dt_util.get_time_zone("Europe/Vienna"))
    yield
    dt_util.set_default_time_zone(original)


def test_build_datetime_definitions_per_heating_circuit():
    defs = build_datetime_definitions({"hk": [0]})
    assert defs["hk0_party_endzeit"]["parameter"] == "CAPPL:LOCAL.hk[0].partyprg_endzeit"
    assert defs["hk0_urlaub_start"]["parameter"] == "CAPPL:LOCAL.hk[0].urlaubsprg_start"
    assert defs["hk0_urlaub_ende"]["parameter"] == "CAPPL:LOCAL.hk[0].urlaubsprg_ende"


def test_build_datetime_definitions_always_includes_device_clock():
    defs = build_datetime_definitions({"hk": []})
    assert set(defs) == {"device_clock"}
    assert defs["device_clock"]["parameter"] == "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu"
    assert defs["device_clock"]["read_parameter"] == "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek"
    assert defs["device_clock"]["commit_parameter"] == "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit"


def _make_entity(coordinator, api=None):
    config = {"parameter": "P", "name": "N", "icon": None}
    return OekofenDateTime(coordinator, api or AsyncMock(), "hk0_party_endzeit", config, entry_id="e1", device_name="Test")


def test_native_value_converts_device_seconds():
    raw = int(datetime(2026, 7, 10, 21, 0, 0, tzinfo=timezone.utc).timestamp())
    coord = FakeCoordinator({"P": make_point(str(raw))})
    entity = _make_entity(coord)

    result = entity.native_value
    local = dt_util.as_local(result)

    assert (local.hour, local.minute) == (21, 0)


def test_native_value_none_when_missing_or_zero():
    assert _make_entity(FakeCoordinator({})).native_value is None
    assert _make_entity(FakeCoordinator({"P": make_point("0")})).native_value is None


async def test_async_set_value_converts_to_device_seconds():
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("0")})
    entity = _make_entity(coord, api=api)
    value = dt_util.as_utc(datetime(2026, 8, 1, 10, 0, 0))

    await entity.async_set_value(value)

    assert api.set_data.await_count == 1
    called_param, called_seconds = api.set_data.call_args[0]
    assert called_param == "P"
    assert isinstance(called_seconds, int)
    assert coord.refresh_calls == 1


def _make_device_clock_entity(coordinator, api=None):
    config = build_datetime_definitions({"hk": []})["device_clock"]
    return OekofenDateTime(coordinator, api or AsyncMock(), "device_clock", config, entry_id="e1", device_name="Test")


def test_device_clock_reads_from_read_parameter_not_write_parameter():
    raw = int(datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point(str(raw))})
    entity = _make_device_clock_entity(coord)

    assert entity.native_value is not None
    assert entity.available is True


def test_device_clock_available_false_when_read_parameter_missing_even_if_write_parameter_present():
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_uhrzeit_neu": make_point("0")})
    entity = _make_device_clock_entity(coord)
    assert entity.available is False


async def test_device_clock_set_value_writes_value_and_commit_flag_together():
    api = AsyncMock()
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point("0")})
    entity = _make_device_clock_entity(coord, api=api)
    value = dt_util.as_utc(datetime(2026, 8, 1, 10, 0, 0))

    await entity.async_set_value(value)

    api.set_data.assert_not_awaited()
    assert api.set_data_multi.await_count == 1
    (sent_values,), _ = api.set_data_multi.call_args
    assert set(sent_values) == {
        "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu",
        "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit",
    }
    assert sent_values["CAPPL:LOCAL.L_fernwartung_setze_uhrzeit"] == 1
    assert coord.refresh_calls == 1


async def test_device_clock_set_value_compensates_devices_own_plus_4h_commit_shift_during_dst():
    """Live-confirmed against a real device (2026-09-05/06, CEST/DST
    active): committing a staged device_clock value via
    L_fernwartung_setze_uhrzeit=1 makes the device's own running clock end
    up 4 hours ahead of whatever was sent - both through this integration
    and through the device's native web UI's own date/time field, so it's
    the device's own commit-time behavior, not a bug in
    datetime_common.py's shared conversion (which the read side and every
    other datetime field remain verified correct against). (An initial
    round found only +2h from a single same-evening data point; a fresh
    page reload the next morning still showed the device 2h ahead of
    actual time even with that -2h compensation applied, revealing the
    real shift during DST is +4h.) Regression test for the -4h
    compensation this needs while Europe/Vienna is on DST (CEST)."""
    api = AsyncMock()
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point("0")})
    entity = _make_device_clock_entity(coord, api=api)
    value = dt_util.as_utc(datetime(2026, 8, 1, 10, 0, 0))  # August: CEST/DST active

    await entity.async_set_value(value)

    (sent_values,), _ = api.set_data_multi.call_args
    uncompensated = datetime_to_device_seconds(value)
    assert sent_values["CAPPL:LOCAL.L_fernwartung_uhrzeit_neu"] == uncompensated - 4 * 3600


async def test_device_clock_set_value_compensates_only_2h_outside_dst():
    """EXPERIMENTAL, unconfirmed hypothesis (see async_commit_device_clock's
    docstring): both live data points calibrating the +4h shift above were
    taken during DST. If the device's actual shift is a fixed, DST-naive
    +2h that only reads as +4h while DST is active, then during CET
    (winter time) only a -2h compensation should be needed. No real
    winter-time data point exists yet to confirm this - this test only
    documents the currently implemented (unverified) behavior so a future
    change here is deliberate, not accidental."""
    api = AsyncMock()
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point("0")})
    entity = _make_device_clock_entity(coord, api=api)
    value = dt_util.as_utc(datetime(2026, 1, 15, 10, 0, 0))  # January: CET/DST inactive

    await entity.async_set_value(value)

    (sent_values,), _ = api.set_data_multi.call_args
    uncompensated = datetime_to_device_seconds(value)
    assert sent_values["CAPPL:LOCAL.L_fernwartung_uhrzeit_neu"] == uncompensated - 2 * 3600
