"""Tests for __init__.py: async_setup_entry orchestration, unload, and
reload.

The setup ordering here matters more than it looks - see coordinator.py's
and __init__.py's own comments on the SETUP_ERROR bug this integration hit:
platforms must be forwarded (registering their needed parameters) before
the coordinator's first refresh runs, and that first refresh must be a
plain async_refresh() rather than async_config_entry_first_refresh() so a
transient failure can't wedge the config entry into a permanent
SETUP_ERROR. test_platforms_forwarded_before_first_coordinator_refresh
below is a direct regression test for that ordering. Dashboard generation
must run *after* the first coordinator refresh too - see
test_dashboard_regenerated_after_first_coordinator_refresh - the dashboard's
structure depends on entity state (warnhinweis attributes, sensor
device_class) that doesn't exist until at least one successful poll.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed

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
    hass.services.has_service.return_value = False
    return hass


@pytest.fixture
def mocks():
    """Patch every external collaborator async_setup_entry talks to, so
    only __init__.py's own orchestration logic is under test."""
    with patch("custom_components.oekofen.PellematicAPI") as api_cls, patch(
        "custom_components.oekofen.async_discover_circuits", new=AsyncMock(return_value={})
    ) as discover, patch("custom_components.oekofen.OekofenCoordinator") as coordinator_cls, patch(
        "custom_components.oekofen.async_regenerate_dashboard", new=AsyncMock()
    ) as regenerate_dashboard, patch(
        "custom_components.oekofen.async_build_wartung_view", new=AsyncMock(return_value=None)
    ) as build_wartung_view:
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
            "regenerate_dashboard": regenerate_dashboard,
            "build_wartung_view": build_wartung_view,
        }


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


async def test_dashboard_regenerated_after_first_coordinator_refresh(mocks):
    """The dashboard's structure depends on entity state that doesn't exist
    until the coordinator's first refresh has actually run (warnhinweis
    attributes, sensor device_class, ...) - generating it any earlier would
    just bake in "unavailable" everywhere."""
    order = []

    async def _refresh():
        order.append("refresh")

    async def _regenerate(*args, **kwargs):
        order.append("regenerate_dashboard")

    mocks["coordinator"].async_refresh.side_effect = _refresh
    mocks["regenerate_dashboard"].side_effect = _regenerate
    hass = _make_hass()

    await async_setup_entry(hass, _make_entry())

    assert order == ["refresh", "regenerate_dashboard"]


async def test_new_wartung_calendar_appearing_later_triggers_regeneration(mocks):
    """If no wartung calendar exists yet when oekofen sets up - a real boot-
    order race, since the calendar's own config entry can load after
    oekofen's within the same bootstrap stage (see the "aber kein
    dashboard"/live-deploy history this integration hit) - the dashboard's
    "Wartung" view must still appear automatically once that calendar shows
    up later, without another restart or a manual
    oekofen.regenerate_dashboard call. Regression test: previously no
    listener at all was registered when async_build_wartung_view found
    nothing at boot, so a later-created calendar was invisible until the
    next restart happened to order things the other way."""
    hass = _make_hass()

    with patch("custom_components.oekofen.async_track_state_added_domain") as track_added:
        await async_setup_entry(hass, _make_entry())

    assert mocks["regenerate_dashboard"].await_count == 1

    track_added.assert_called_once()
    args, _ = track_added.call_args
    assert args[1] == ["calendar"]
    on_new_calendar = args[2]

    new_state = MagicMock()
    new_state.attributes = {"friendly_name": "Ofen Wartung"}
    event = MagicMock()
    event.data = {"entity_id": "calendar.ofen_wartung", "new_state": new_state}

    await on_new_calendar(event)

    assert mocks["regenerate_dashboard"].await_count == 2


async def test_new_non_wartung_calendar_does_not_trigger_regeneration(mocks):
    """A newly-added calendar with an unrelated name (e.g. a shared family
    calendar) must not spuriously re-trigger dashboard generation."""
    hass = _make_hass()

    with patch("custom_components.oekofen.async_track_state_added_domain") as track_added:
        await async_setup_entry(hass, _make_entry())

    assert mocks["regenerate_dashboard"].await_count == 1
    on_new_calendar = track_added.call_args[0][2]

    new_state = MagicMock()
    new_state.attributes = {"friendly_name": "Familie"}
    event = MagicMock()
    event.data = {"entity_id": "calendar.familie", "new_state": new_state}

    await on_new_calendar(event)

    assert mocks["regenerate_dashboard"].await_count == 1


async def test_first_refresh_uses_async_refresh_not_config_entry_first_refresh(mocks):
    """async_config_entry_first_refresh() raises ConfigEntryNotReady on
    failure, which re-triggers this whole function without unloading the
    platforms from the failed attempt - see __init__.py's comment. Must
    stay on the non-raising async_refresh()."""
    hass = _make_hass()

    await async_setup_entry(hass, _make_entry())

    mocks["coordinator"].async_refresh.assert_awaited_once()
    mocks["coordinator"].async_config_entry_first_refresh.assert_not_called()


async def test_setup_raises_auth_failed_on_bad_credentials(mocks):
    """A clean "wrong credentials" response must surface as
    ConfigEntryAuthFailed, not a bare False return - that's what makes HA
    offer a reauthenticate repair in Settings instead of leaving the entry
    failed with no indication of why or how to fix it."""
    mocks["api"].authenticate.return_value = False
    hass = _make_hass()

    with pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, _make_entry())

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


async def test_setup_registers_regenerate_dashboard_service(mocks):
    hass = _make_hass()

    await async_setup_entry(hass, _make_entry())

    hass.services.async_register.assert_called_once()
    args, _ = hass.services.async_register.call_args
    assert args[0] == DOMAIN
    assert args[1] == "regenerate_dashboard"


async def test_setup_skips_registering_service_twice(mocks):
    hass = _make_hass()
    hass.services.has_service.return_value = True

    await async_setup_entry(hass, _make_entry())

    hass.services.async_register.assert_not_called()


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
