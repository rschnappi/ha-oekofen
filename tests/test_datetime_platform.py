"""Tests for the datetime platform (datetime.py) - Party-/Urlaubsprogramm fields."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.oekofen.datetime import (
    OekofenDateTime,
    build_datetime_definitions,
)

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


def test_build_datetime_definitions_empty_without_circuits():
    assert build_datetime_definitions({"hk": []}) == {}


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
