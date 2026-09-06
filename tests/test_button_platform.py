"""Tests for the button platform (button.py) - device clock sync button."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.oekofen.button import OekofenSyncClockButton
from custom_components.oekofen.datetime_common import datetime_to_device_seconds

from .conftest import FakeCoordinator, make_point


@pytest.fixture(autouse=True)
def vienna_timezone():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(dt_util.get_time_zone("Europe/Vienna"))
    yield
    dt_util.set_default_time_zone(original)


def _make_button(coordinator, api=None):
    return OekofenSyncClockButton(coordinator, api or AsyncMock(), "e1", "Test")


def test_available_reflects_device_clock_read_parameter():
    raw = int(datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point(str(raw))})
    assert _make_button(coord).available is True

    assert _make_button(FakeCoordinator({})).available is False


async def test_press_commits_current_time_with_minus_4h_compensation(monkeypatch):
    api = AsyncMock()
    coord = FakeCoordinator({"CAPPL:LOCAL.L_fernwartung_datum_zeit_sek": make_point("0")})
    button = _make_button(coord, api=api)

    fixed_now = dt_util.as_utc(datetime(2026, 8, 1, 10, 0, 0))
    monkeypatch.setattr(dt_util, "utcnow", lambda: fixed_now)

    await button.async_press()

    api.set_data.assert_not_awaited()
    assert api.set_data_multi.await_count == 1
    (sent_values,), _ = api.set_data_multi.call_args
    assert set(sent_values) == {
        "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu",
        "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit",
    }
    assert sent_values["CAPPL:LOCAL.L_fernwartung_setze_uhrzeit"] == 1
    uncompensated = datetime_to_device_seconds(fixed_now)
    assert sent_values["CAPPL:LOCAL.L_fernwartung_uhrzeit_neu"] == uncompensated - 4 * 3600
    assert coord.refresh_calls == 1
