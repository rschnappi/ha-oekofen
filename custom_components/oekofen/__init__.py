"""The ÖkOfen Pellematic integration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import (
    async_track_state_added_domain,
    async_track_state_change_event,
)

from .coordinator import OekofenCoordinator
from .dashboard import async_build_wartung_view, async_regenerate_dashboard, matches_wartung
from .discovery import async_discover_circuits
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"
SERVICE_REGENERATE_DASHBOARD = "regenerate_dashboard"

PLATFORMS = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
    Platform.DATETIME,
    Platform.CLIMATE,
    Platform.TEXT,
    Platform.BUTTON,
]


async def _async_regenerate_dashboard_and_track_calendar(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Build the auto-managed ÖkOfen dashboard (see dashboard.py), then keep
    it in sync with the maintenance calendar without requiring a restart:
    whenever that calendar's state changes - a new/edited/deleted
    appointment - re-running the dashboard build picks up the change and
    saves it, which in turn tells any already-open dashboard tab to refetch
    (see LovelaceStorage.async_save's EVENT_LOVELACE_UPDATED).
    """
    await async_regenerate_dashboard(hass)

    # Always watch for a wartung-looking calendar entity newly *appearing*
    # (not just changing) - the calendar entity's own config entry can set
    # up after oekofen's within the same bootstrap stage, so on some boots
    # it doesn't exist yet at the point above. Without this, a dashboard
    # built before that calendar existed would never get its "Wartung" view
    # added until a manual oekofen.regenerate_dashboard call or another
    # restart that happens to order things the other way.
    async def _on_new_calendar(event) -> None:
        entity_id = event.data["entity_id"]
        if matches_wartung(entity_id, event.data.get("new_state")):
            await async_regenerate_dashboard(hass)

    entry.async_on_unload(
        async_track_state_added_domain(hass, ["calendar"], _on_new_calendar)
    )

    wartung_view = await async_build_wartung_view(hass)
    if not wartung_view:
        return
    calendar_entity_id = wartung_view["cards"][1]["entities"][0]

    async def _on_calendar_changed(event) -> None:
        await async_regenerate_dashboard(hass)

    entry.async_on_unload(
        async_track_state_change_event(hass, [calendar_entity_id], _on_calendar_changed)
    )


async def _async_setup_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_REGENERATE_DASHBOARD):
        return

    async def _handle_regenerate_dashboard(call: ServiceCall) -> None:
        await async_regenerate_dashboard(hass)

    hass.services.async_register(DOMAIN, SERVICE_REGENERATE_DASHBOARD, _handle_regenerate_dashboard, schema=vol.Schema({}))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ÖkOfen from a config entry."""

    # Extract configuration
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    language = entry.data.get("language", "de")

    # Ensure URL format
    if not host.startswith(('http://', 'https://')):
        host = f"http://{host}"

    # Create API instance
    api = PellematicAPI(host, username, password, language)

    # Test connection
    try:
        authenticated = await api.authenticate()
    except Exception as e:
        _LOGGER.error(f"Failed to connect to ÖkOfen device: {e}")
        return False

    if not authenticated:
        # A clean "wrong credentials" response (as opposed to the network/
        # connection exceptions caught above) - raise so HA offers a
        # reauthenticate repair in Settings instead of just failing setup
        # with no indication of why or how to fix it.
        raise ConfigEntryAuthFailed("Authentication failed - check username/password")

    # Discover which heating circuits, hot-water circuits, circulation
    # pumps and Pellematic units actually exist on this device, so the
    # schedule/number/select platforms only create entities for hardware
    # that is really there.
    circuits = await async_discover_circuits(api)

    # Shared coordinator: platforms register the parameters they need into
    # it during their own async_setup_entry (called via
    # async_forward_entry_setups below), then we trigger a single first
    # refresh once every platform has registered - see coordinator.py.
    coordinator = OekofenCoordinator(hass, api, entry)

    # Store API instance
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "circuits": circuits,
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # All platforms have registered their needed parameters into the shared
    # coordinator by now (async_forward_entry_setups awaits every platform's
    # async_setup_entry) - fetch them all in one combined request.
    #
    # Deliberately async_refresh(), not async_config_entry_first_refresh():
    # the latter raises ConfigEntryNotReady on failure, which makes HA retry
    # this whole async_setup_entry - including the async_forward_entry_setups
    # above - without unloading the platforms from the failed attempt first,
    # so EntityComponent rejects the retry ("already been setup") and the
    # entry lands in a permanent SETUP_ERROR. A transient failure on the very
    # first request against the device's fairly weak embedded web server
    # (e.g. right after this device or HA itself has just restarted) would
    # brick the integration until a manual reload. async_refresh() only logs
    # and leaves last_update_success False instead - entities already
    # tolerate that (coordinator.data stays {}, see coordinator.py), showing
    # unavailable until the coordinator's own next scheduled poll succeeds.
    await coordinator.async_refresh()

    # Build (or refresh) the auto-managed ÖkOfen dashboard now that every
    # entity exists with real state - including "warnhinweis" attributes and
    # the maintenance calendar's events, both of which the dashboard's
    # structure depends on. This is a plain, static Lovelace config (see
    # dashboard.py for why, replacing the old client-side dashboard-strategy
    # JS), so it renders reliably on every load with nothing for a client to
    # race against - including right after this very restart.
    await _async_regenerate_dashboard_and_track_calendar(hass, entry)
    await _async_setup_services(hass)

    # Register update listener for options flow (enables reload button)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(f"ÖkOfen integration setup complete for {host}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Close API connection
        api_data = hass.data[DOMAIN][entry.entry_id]
        if "api" in api_data:
            await api_data["api"].close()

        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)

        _LOGGER.info("ÖkOfen integration unloaded successfully")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry.

    Goes through hass.config_entries.async_reload() rather than calling
    async_unload_entry/async_setup_entry directly - that's HA's own reload
    entry point, and it takes the entry's setup lock and handles the
    SETUP_IN_PROGRESS state transition, so two update-listener firings close
    together (e.g. a fast double-submit of the options flow) can't race each
    other the way two bare unload+setup calls could.
    """
    await hass.config_entries.async_reload(entry.entry_id)
