"""Tests for the shared OekofenCoordinator (coordinator.py).

Every platform used to run its own DataUpdateCoordinator; they're now
consolidated into one shared instance per config entry (see __init__.py),
which platforms register their needed parameters into via add_parameters()
before __init__.py triggers a single first refresh. These tests exercise
that logic directly - constructed via object.__new__ to skip
DataUpdateCoordinator.__init__ (which needs a real hass/event loop), since
_async_update_data only touches self.api/self.parameters, matching the
"test the logic, not the HA plumbing" style used throughout this repo's
other tests (see FakeCoordinator in conftest.py).
"""
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.oekofen.coordinator import OekofenCoordinator


def _make_coordinator(api=None) -> OekofenCoordinator:
    coordinator = object.__new__(OekofenCoordinator)
    coordinator.api = api or AsyncMock()
    coordinator.parameters = set()
    return coordinator


def test_add_parameters_accumulates_across_calls():
    coordinator = _make_coordinator()
    coordinator.add_parameters(["a", "b"])
    coordinator.add_parameters(["b", "c"])
    assert coordinator.parameters == {"a", "b", "c"}


async def test_update_data_fetches_all_registered_parameters():
    api = AsyncMock()
    api.get_data.return_value = {"a": {"value": "1"}}
    coordinator = _make_coordinator(api)
    coordinator.add_parameters(["a", "b", "c"])

    result = await coordinator._async_update_data()

    api.get_data.assert_awaited_once()
    (requested,), _ = api.get_data.call_args
    assert set(requested) == {"a", "b", "c"}
    assert result == {"a": {"value": "1"}}


async def test_update_data_wraps_errors_in_update_failed():
    api = AsyncMock()
    api.get_data.side_effect = RuntimeError("boom")
    coordinator = _make_coordinator(api)
    coordinator.add_parameters(["a"])

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_data_raises_auth_failed_when_credentials_are_the_problem():
    """A technician password changed after setup must surface as
    ConfigEntryAuthFailed (which DataUpdateCoordinator itself specifically
    detects and turns into a reauthenticate repair), not just another
    UpdateFailed that leaves entities unavailable with no indication why."""
    api = AsyncMock()
    api.get_data.side_effect = Exception("Authentication failed")
    coordinator = _make_coordinator(api)
    coordinator.add_parameters(["a"])

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
