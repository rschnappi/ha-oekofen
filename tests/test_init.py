"""Tests for __init__.py: async_setup_entry orchestration, unload, and
reload.

The setup ordering here matters more than it looks - see coordinator.py's
and __init__.py's own comments on the SETUP_ERROR bug this integration hit:
platforms must be forwarded (registering their needed parameters) before
the coordinator's first refresh runs, and that first refresh must be a
plain async_refresh() rather than async_config_entry_first_refresh() so a
transient failure can't wedge the config entry into a permanent
SETUP_ERROR. test_platforms_forwarded_before_first_coordinator_refresh
below is a direct regression test for that ordering.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.oekofen import (
    DOMAIN,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)


def _make_entry(entry_id="entry1"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {
        "host": "192.0.2.1",
        "username": "user",
        "password": "pass",
    }
    entry.add_update_listener.return_value = "unsub"
    return entry


def _make_hass():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    hass.http.async_register_static_paths = AsyncMock()
    return hass


@pytest.fixture
def mocks():
    """Patch every external collaborator async_setup_entry talks to, so
    only __init__.py's own orchestration logic is under test."""
    with patch("custom_components.oekofen.PellematicAPI") as api_cls, patch(
        "custom_components.oekofen.async_discover_circuits", new=AsyncMock(return_value={})
    ) as discover, patch("custom_components.oekofen.OekofenCoordinator") as coordinator_cls, patch(
        "custom_components.oekofen.add_extra_js_url"
    ):
        api = AsyncMock()
        api.authenticate = AsyncMock(return_value=True)
        api_cls.return_value = api

        coordinator = MagicMock()
        coordinator.async_refresh = AsyncMock()
        coordinator_cls.return_value = coordinator

        yield {
            "api_cls": api_cls,
            "api": api,
            "discover": discover,
            "coordinator_cls": coordinator_cls,
            "coordinator": coordinator,
        }


async def test_frontend_resources_registered_before_any_device_network_io(mocks):
    """A dashboard loading "strategy: custom:oekofen-strategy" needs the JS
    resource registered before it renders - e.g. a kiosk tablet reconnecting
    as soon as HA/frontend is reachable, which can happen before this
    integration finishes its own setup. authenticate()/async_discover_
    circuits() are real network round-trips to the device that can easily
    take a few seconds, so the frontend registration (a purely local,
    hass-only operation) must happen before them, not after - see
    __init__.py's comment on the "Timeout waiting for strategy element ...
    to be registered" error this caused."""
    order = []

    async def _authenticate():
        order.append("authenticate")
        return True

    def _add_extra_js_url(*args, **kwargs):
        order.append("register_frontend")

    hass = _make_hass()
    mocks["api"].authenticate.side_effect = _authenticate

    with patch("custom_components.oekofen.add_extra_js_url", side_effect=_add_extra_js_url):
        await async_setup_entry(hass, _make_entry())

    assert order == ["register_frontend", "authenticate"]


async def test_platforms_forwarded_before_first_coordinator_refresh(mocks):
    """Regression test for the SETUP_ERROR bug: entities are added inside
    each platform's async_setup_entry, so all platforms must finish
    registering their parameters before the coordinator's first refresh -
    reversing this order was the original coordinator.data-is-None crash,
    and combining a raising first-refresh with this order is what caused
    the later permanent-SETUP_ERROR bug."""
    order = []

    async def _forward(*args, **kwargs):
        order.append("forward")

    async def _refresh():
        order.append("refresh")

    hass = _make_hass()
    hass.config_entries.async_forward_entry_setups.side_effect = _forward
    mocks["coordinator"].async_refresh.side_effect = _refresh

    result = await async_setup_entry(hass, _make_entry())

    assert result is True
    assert order == ["forward", "refresh"]


async def test_first_refresh_uses_async_refresh_not_config_entry_first_refresh(mocks):
    """async_config_entry_first_refresh() raises ConfigEntryNotReady on
    failure, which re-triggers this whole function without unloading the
    platforms from the failed attempt - see __init__.py's comment. Must
    stay on the non-raising async_refresh()."""
    hass = _make_hass()

    await async_setup_entry(hass, _make_entry())

    mocks["coordinator"].async_refresh.assert_awaited_once()
    mocks["coordinator"].async_config_entry_first_refresh.assert_not_called()


async def test_setup_returns_false_and_stops_early_on_auth_failure(mocks):
    mocks["api"].authenticate.return_value = False
    hass = _make_hass()

    result = await async_setup_entry(hass, _make_entry())

    assert result is False
    hass.config_entries.async_forward_entry_setups.assert_not_called()
    mocks["coordinator"].async_refresh.assert_not_called()


async def test_setup_returns_false_on_connection_exception(mocks):
    mocks["api"].authenticate.side_effect = OSError("connection refused")
    hass = _make_hass()

    result = await async_setup_entry(hass, _make_entry())

    assert result is False
    hass.config_entries.async_forward_entry_setups.assert_not_called()


async def test_setup_stores_api_circuits_and_coordinator_in_hass_data(mocks):
    mocks["discover"].return_value = {"hk": [0]}
    hass = _make_hass()
    entry = _make_entry("entry1")

    await async_setup_entry(hass, entry)

    entry_data = hass.data[DOMAIN]["entry1"]
    assert entry_data["api"] is mocks["api"]
    assert entry_data["circuits"] == {"hk": [0]}
    assert entry_data["coordinator"] is mocks["coordinator"]


async def test_unload_closes_api_and_removes_entry_data_on_success(mocks):
    hass = _make_hass()
    entry = _make_entry("entry1")
    await async_setup_entry(hass, entry)

    result = await async_unload_entry(hass, entry)

    assert result is True
    mocks["api"].close.assert_awaited_once()
    assert "entry1" not in hass.data[DOMAIN]


async def test_unload_keeps_entry_data_when_platform_unload_fails(mocks):
    hass = _make_hass()
    entry = _make_entry("entry1")
    await async_setup_entry(hass, entry)
    hass.config_entries.async_unload_platforms.return_value = False

    result = await async_unload_entry(hass, entry)

    assert result is False
    mocks["api"].close.assert_not_called()
    assert "entry1" in hass.data[DOMAIN]


async def test_reload_entry_uses_hass_config_entries_async_reload():
    """Must go through HA's own reload entry point (setup lock +
    SETUP_IN_PROGRESS handling), not a manual unload+setup chain that could
    race a fast double-submit of the options flow."""
    hass = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    entry = _make_entry("entry1")

    await async_reload_entry(hass, entry)

    hass.config_entries.async_reload.assert_awaited_once_with("entry1")
