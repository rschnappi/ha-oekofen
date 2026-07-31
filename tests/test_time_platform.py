"""Tests for the time platform (time.py)."""
from datetime import time as dt_time
from unittest.mock import AsyncMock

from custom_components.oekofen.schedule_common import build_schedule_slots
from custom_components.oekofen.time import OekofenScheduleTimeEntity

from .conftest import FakeCoordinator, make_point


def _slot():
    return build_schedule_slots({"hk": [0], "ww": [], "zirkp": []})[0]


def _make_entity(coordinator, block=0, edge=0, api=None):
    return OekofenScheduleTimeEntity(
        coordinator, api or AsyncMock(), _slot(), block, edge, entry_id="e1", device_name="Test"
    )


def test_parameter_includes_block_and_edge():
    entity = _make_entity(FakeCoordinator({}), block=1, edge=0)
    assert entity._parameter == f"{_slot()['base']}.zeitreihe[1,0]"


def test_native_value_converts_seconds_to_time():
    param = f"{_slot()['base']}.zeitreihe[0,0]"
    coord = FakeCoordinator({param: make_point("64800")})  # 18:00:00
    entity = _make_entity(coord, block=0, edge=0)
    assert entity.native_value == dt_time(18, 0, 0)


def test_native_value_none_when_missing():
    entity = _make_entity(FakeCoordinator({}), block=0, edge=0)
    assert entity.native_value is None


async def test_async_set_value_converts_time_to_seconds():
    param = f"{_slot()['base']}.zeitreihe[0,1]"
    api = AsyncMock()
    coord = FakeCoordinator({param: make_point("0")})
    entity = _make_entity(coord, block=0, edge=1, api=api)

    await entity.async_set_value(dt_time(21, 0, 0))

    api.set_data.assert_awaited_once_with(param, 21 * 3600)
    assert coord.refresh_calls == 1


def test_unique_id_distinguishes_block_and_edge():
    entity_start = _make_entity(FakeCoordinator({}), block=0, edge=0)
    entity_end = _make_entity(FakeCoordinator({}), block=0, edge=1)
    assert entity_start.unique_id != entity_end.unique_id
    assert entity_start.unique_id.endswith("_block0_von")
    assert entity_end.unique_id.endswith("_block0_bis")
