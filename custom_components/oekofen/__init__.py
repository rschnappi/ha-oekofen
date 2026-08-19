"""The ÖkOfen Pellematic integration."""
import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .coordinator import OekofenCoordinator
from .discovery import async_discover_circuits
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"
STRATEGY_URL_PATH = "/oekofen_static/oekofen-strategy.js"
_FRONTEND_KEY = "_frontend_registered"

# Read once at import time (module import already runs off the event loop),
# not inside the async setup below, to avoid HA's blocking-call detector.
_MANIFEST_VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
PLATFORMS = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
    Platform.DATETIME,
    Platform.CLIMATE,
    Platform.TEXT,
]


async def _async_register_frontend_resources(hass: HomeAssistant) -> None:
    """Serve the bundled ÖkOfen dashboard-strategy JS and register it with the
    frontend, so `strategy: {type: custom:oekofen-strategy}` works without the
    user manually adding a Lovelace resource. Idempotent across config
    entries/reloads.
    """
    if hass.data.setdefault(DOMAIN, {}).get(_FRONTEND_KEY):
        return
    hass.data[DOMAIN][_FRONTEND_KEY] = True

    js_path = str(Path(__file__).parent / "www" / "oekofen-strategy.js")
    try:
        # HA >= ~2024.7: async, avoids the "blocking call" warning the sync
        # register_static_path below triggers on newer versions.
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(STRATEGY_URL_PATH, js_path, cache_headers=False)]
        )
    except ImportError:
        # Older HA doesn't have StaticPathConfig/async_register_static_paths yet.
        hass.http.register_static_path(STRATEGY_URL_PATH, js_path, cache_headers=False)

    # Cache-bust with the integration version, so browsers fetch the new JS
    # after an update instead of serving a stale cached copy of the module
    # under the same URL until the user manually clears their cache.
    add_extra_js_url(hass, f"{STRATEGY_URL_PATH}?v={_MANIFEST_VERSION}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ÖkOfen from a config entry."""

    # Register the dashboard-strategy JS first, before any network I/O to
    # the device below (authenticate/discover circuits) - those can easily
    # take a few seconds, and a dashboard loading a "strategy:
    # custom:oekofen-strategy" view in that window (e.g. a kiosk tablet
    # reconnecting as soon as HA/frontend is reachable, which can happen
    # before this integration's own setup finishes) gets HA's frontend
    # index.html rendered without our script tag yet - "Timeout waiting for
    # strategy element ... to be registered", unrelated to browser caching.
    # This call has no dependency on api/circuits/coordinator, so it's safe
    # to run first.
    await _async_register_frontend_resources(hass)

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
        if not await api.authenticate():
            _LOGGER.error("Failed to authenticate with ÖkOfen device")
            return False
    except Exception as e:
        _LOGGER.error(f"Failed to connect to ÖkOfen device: {e}")
        return False
    
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