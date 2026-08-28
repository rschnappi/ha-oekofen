"""The ÖkOfen Pellematic integration."""
import asyncio
import hashlib
import json
import logging
from pathlib import Path

from aiohttp import web

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

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


class _StrategyJSView(HomeAssistantView):
    """Serves the bundled dashboard-strategy JS, cacheable *because* its URL
    is version-busted.

    The URL always carries ?v=<manifest version> (see add_extra_js_url
    below), so a given URL's content never changes - which makes
    "immutable" both correct and, more importantly, necessary.

    This deliberately replaces the earlier no-store header, which caused a
    worse bug than the one it was meant to fix:

    HA's frontend gives a custom dashboard strategy only a couple of
    seconds to register its custom element before giving up with "Timeout
    waiting for strategy element ll-strategy-dashboard-oekofen-strategy to
    be registered". With no-store, every single dashboard load had to
    complete a fresh network round-trip for this file inside that window,
    with no local copy to fall back on. A desktop browser on the LAN does
    that in milliseconds and never notices; the Android companion app's
    WebView - cold-started, competing with the rest of the frontend bundle
    and the user's other custom-card resources - regularly did not, and
    failed with exactly that timeout on every attempt, over WLAN, mobile
    and VPN alike, and *more* reliably right after clearing its cache.

    no-store was also aimed at the wrong resource: the JS is already
    version-busted, so it cannot go stale. What can go stale is HA's
    index.html, which is what carries the <script type="module"> tag
    pointing at this URL - and a no-store header on the JS does nothing
    about that.

    Caching it properly means each client fetches a given version once and
    then registers the element straight from its local cache on every
    later load, well inside the frontend's timeout. The trade-off is that
    editing the JS *without* bumping manifest.json's version leaves
    clients on the old copy indefinitely - that version bump is already
    mandatory for any JS change (see CLAUDE.md).

    The ETag/304 path only matters for clients that revalidate anyway
    despite "immutable" (some proxies, some WebViews): they get an empty
    304 instead of the full body, which is still fast enough to beat the
    strategy timeout.
    """

    url = STRATEGY_URL_PATH
    name = "oekofen_strategy_js"
    requires_auth = False

    def __init__(self, js_content: str) -> None:
        self._js_content = js_content
        # Hash the content rather than reusing the manifest version, so the
        # ETag stays honest even if a JS edit ever does ship without the
        # required version bump.
        self._etag = f'"{hashlib.sha256(js_content.encode()).hexdigest()[:32]}"'

    def _cache_headers(self) -> dict[str, str]:
        return {
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": self._etag,
        }

    async def get(self, request: web.Request) -> web.Response:
        # If-None-Match may carry several candidates, and/or a weak ("W/")
        # prefix a proxy added along the way - match on the bare tag.
        if_none_match = request.headers.get("If-None-Match", "")
        candidates = {
            candidate.strip().removeprefix("W/")
            for candidate in if_none_match.split(",")
            if candidate.strip()
        }
        if self._etag in candidates:
            return web.Response(status=304, headers=self._cache_headers())

        return web.Response(
            text=self._js_content,
            content_type="application/javascript",
            headers=self._cache_headers(),
        )


async def _async_register_frontend_resources(hass: HomeAssistant) -> None:
    """Serve the bundled ÖkOfen dashboard-strategy JS and register it with the
    frontend, so `strategy: {type: custom:oekofen-strategy}` works without the
    user manually adding a Lovelace resource. Idempotent across config
    entries/reloads.

    With two ÖkOfen devices configured, HA sets up both config entries
    concurrently, and this is the very first thing each one does. A bare
    "already registered" boolean would let a second, concurrent call return
    immediately while the first call is still mid-`await` on the actual
    registration - reopening (in a much narrower window) the same "Timeout
    waiting for strategy element ... to be registered" race this function was
    reordered to fix in the first place. An Event lets a concurrent caller
    wait for registration to actually finish instead of racing past it.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    existing_event = domain_data.get(_FRONTEND_KEY)
    if existing_event is not None:
        await existing_event.wait()
        return

    event = asyncio.Event()
    domain_data[_FRONTEND_KEY] = event
    try:
        js_path = Path(__file__).parent / "www" / "oekofen-strategy.js"
        js_content = await hass.async_add_executor_job(js_path.read_text)
        hass.http.register_view(_StrategyJSView(js_content))

        # The version in the query string is what makes the view's long
        # immutable Cache-Control above safe: an update changes the URL, so
        # every client refetches exactly once per version and serves it from
        # its own cache on every load after that - fast enough to register
        # the strategy element inside the frontend's registration timeout
        # even on a slow WebView. See _StrategyJSView's docstring.
        add_extra_js_url(hass, f"{STRATEGY_URL_PATH}?v={_MANIFEST_VERSION}")
    finally:
        event.set()


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