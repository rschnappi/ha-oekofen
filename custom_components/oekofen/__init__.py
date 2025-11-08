"""The ÖkOfen Pellematic integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ÖkOfen Pellematic from a config entry."""
    
    # Extract configuration
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    # Ensure URL format
    if not host.startswith(('http://', 'https://')):
        host = f"http://{host}"
    
    # Create API instance
    api = PellematicAPI(host, username, password)
    
    # Test connection
    try:
        if not await api.authenticate():
            _LOGGER.error("Failed to authenticate with ÖkOfen device")
            return False
    except Exception as e:
        _LOGGER.error(f"Failed to connect to ÖkOfen device: {e}")
        return False
    
    # Store API instance
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
    }
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
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
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)