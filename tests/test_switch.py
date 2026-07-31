"""Tests for the switch platform (switch.py)."""
from unittest.mock import AsyncMock

from custom_components.oekofen.switch import (
    OekofenDayActiveSwitch,
    OekofenModeSwitch,
    build_mode_switch_definitions,
)
from custom_components.oekofen.schedule_common import build_schedule_slots

from .conftest import FakeCoordinator, make_point


def test_build_mode_switch_definitions():
    defs = build_mode_switch_definitions({"hk": [0], "ww": [0]})
    assert defs["hk0_party_aktiviert"]["parameter"] == "CAPPL:LOCAL.hk[0].partyprg_aktiviert"
    assert defs["hk0_urlaub_aktiviert"]["parameter"] == "CAPPL:LOCAL.hk[0].urlaubsprg_aktiviert"
    assert defs["ww0_einmal_aufbereiten"]["parameter"] == "CAPPL:LOCAL.ww[0].einmal_aufbereiten"


def test_build_mode_switch_definitions_empty_for_no_circuits():
    assert build_mode_switch_definitions({"hk": [], "ww": []}) == {}


def _day_slot():
    return build_schedule_slots({"hk": [0], "ww": [], "zirkp": []})[0]


def _make_day_switch(coordinator, api=None):
    return OekofenDayActiveSwitch(coordinator, api or AsyncMock(), _day_slot(), entry_id="e1", device_name="Test")


def test_day_switch_is_on_when_block_not_minus_one():
    param = f"{_day_slot()['base']}.block"
    coord = FakeCoordinator({param: make_point("0")})
    assert _make_day_switch(coord).is_on is True


def test_day_switch_is_off_when_block_is_minus_one():
    param = f"{_day_slot()['base']}.block"
    coord = FakeCoordinator({param: make_point("-1")})
    assert _make_day_switch(coord).is_on is False


def test_day_switch_is_none_when_value_missing():
    assert _make_day_switch(FakeCoordinator({})).is_on is None


async def test_day_switch_turn_on_writes_zero():
    api = AsyncMock()
    param = f"{_day_slot()['base']}.block"
    coord = FakeCoordinator({param: make_point("-1")})
    switch = _make_day_switch(coord, api=api)

    await switch.async_turn_on()

    api.set_data.assert_awaited_once_with(param, 0)
    assert coord.refresh_calls == 1


async def test_day_switch_turn_off_writes_minus_one():
    api = AsyncMock()
    param = f"{_day_slot()['base']}.block"
    coord = FakeCoordinator({param: make_point("0")})
    switch = _make_day_switch(coord, api=api)

    await switch.async_turn_off()

    api.set_data.assert_awaited_once_with(param, -1)


def _make_mode_switch(coordinator, config, api=None):
    return OekofenModeSwitch(coordinator, api or AsyncMock(), "hk0_party_aktiviert", config, entry_id="e1", device_name="Test")


def test_mode_switch_is_on_for_value_one():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({"P": make_point("1")})
    assert _make_mode_switch(coord, config).is_on is True


def test_mode_switch_is_off_for_value_zero():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({"P": make_point("0")})
    assert _make_mode_switch(coord, config).is_on is False


async def test_mode_switch_turn_on_off_write_expected_values():
    config = {"parameter": "P", "name": "N", "icon": None}
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("0")})
    switch = _make_mode_switch(coord, config, api=api)

    await switch.async_turn_on()
    api.set_data.assert_awaited_with("P", 1)

    await switch.async_turn_off()
    api.set_data.assert_awaited_with("P", 0)


def test_available_false_when_coordinator_failed():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({"P": make_point("1")}, last_update_success=False)
    assert _make_mode_switch(coord, config).available is False
