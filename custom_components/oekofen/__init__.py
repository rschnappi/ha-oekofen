"""The ÖkOfen Pellematic integration."""
import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"
PLATFORMS = [Platform.SENSOR]

# Service schemas
SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = vol.Schema({
    vol.Required("parameter"): cv.string,
    vol.Required("value"): vol.Any(vol.Coerce(float), vol.Coerce(int), cv.string),
    vol.Optional("divisor"): vol.Coerce(int),
})

SERVICE_SET_SYSTEM_MODE = "set_system_mode"
SERVICE_SET_SYSTEM_MODE_SCHEMA = vol.Schema({
    vol.Required("mode"): vol.In(["aus", "auto", "warmwasser"]),
})

SERVICE_SET_HEATING_MODE = "set_heating_mode"
SERVICE_SET_HEATING_MODE_SCHEMA = vol.Schema({
    vol.Optional("circuit", default=0): vol.In([0, 1, 2, 3, 4, 5]),
    vol.Required("mode"): vol.In(["aus", "auto", "heizen", "absenken"]),
})

SERVICE_SET_HOT_WATER_MODE = "set_hot_water_mode"
SERVICE_SET_HOT_WATER_MODE_SCHEMA = vol.Schema({
    vol.Optional("circuit", default=0): vol.In([0, 1, 2]),
    vol.Required("mode"): vol.In(["aus", "auto", "ein"]),
})

SERVICE_SET_PELLEMATIC_MODE = "set_pellematic_mode"
SERVICE_SET_PELLEMATIC_MODE_SCHEMA = vol.Schema({
    vol.Optional("unit", default=0): vol.In([0, 1, 2, 3]),
    vol.Required("mode"): vol.In(["aus", "auto", "ein"]),
})


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
    
    # Register services
    async def handle_set_parameter(call: ServiceCall) -> None:
        """Handle the set_parameter service call."""
        parameter = call.data["parameter"]
        value = call.data["value"]
        divisor = call.data.get("divisor")
        
        try:
            result = await api.set_data(parameter, value, divisor)
            _LOGGER.info(f"Service call successful: {result}")
        except Exception as e:
            _LOGGER.error(f"Service call failed: {e}")
            raise
    
    async def handle_set_system_mode(call: ServiceCall) -> None:
        """Handle the set_system_mode service call."""
        mode = call.data["mode"]
        
        # Map mode names to values
        # Anlage: Aus - Auto - Warmwasser
        mode_map = {
            "aus": 0,
            "auto": 1,
            "warmwasser": 2,
        }
        
        parameter = "CAPPL:LOCAL.anlage_betriebsart"
        value = mode_map[mode]
        
        _LOGGER.info(f"Setting system mode to {mode} (value={value})")
        
        try:
            result = await api.set_data(parameter, value, divisor=None)
            _LOGGER.info(f"Service call successful: {result}")
        except Exception as e:
            _LOGGER.error(f"Service call failed: {e}")
            raise
    
    async def handle_set_heating_mode(call: ServiceCall) -> None:
        """Handle the set_heating_mode service call."""
        circuit = call.data["circuit"]
        mode = call.data["mode"]
        
        # Map mode names to values
        # Heizkreis: Aus - Auto - Heizen - Absenken
        mode_map = {
            "aus": 0,
            "auto": 1,
            "heizen": 2,
            "absenken": 3,
        }
        
        parameter = f"CAPPL:LOCAL.hk[{circuit}].betriebsart[0]"
        value = mode_map[mode]
        
        _LOGGER.info(f"Setting heating circuit {circuit} mode to {mode} (value={value})")
        
        try:
            result = await api.set_data(parameter, value, divisor=None)
            _LOGGER.info(f"Service call successful: {result}")
        except Exception as e:
            _LOGGER.error(f"Service call failed: {e}")
            raise
    
    async def handle_set_hot_water_mode(call: ServiceCall) -> None:
        """Handle the set_hot_water_mode service call."""
        circuit = call.data["circuit"]
        mode = call.data["mode"]
        
        # Map mode names to values
        # Warmwasser: Aus - Auto - Ein
        mode_map = {
            "aus": 0,
            "auto": 1,
            "ein": 2,
        }
        
        parameter = f"CAPPL:LOCAL.ww[{circuit}].betriebsart[0]"
        value = mode_map[mode]
        
        _LOGGER.info(f"Setting hot water circuit {circuit} mode to {mode} (value={value})")
        
        try:
            result = await api.set_data(parameter, value, divisor=None)
            _LOGGER.info(f"Service call successful: {result}")
        except Exception as e:
            _LOGGER.error(f"Service call failed: {e}")
            raise
    
    async def handle_set_pellematic_mode(call: ServiceCall) -> None:
        """Handle the set_pellematic_mode service call."""
        unit = call.data["unit"]
        mode = call.data["mode"]
        
        # Map mode names to values
        # Pellematic: Aus - Auto - Ein
        mode_map = {
            "aus": 0,
            "auto": 1,
            "ein": 2,
        }
        
        parameter = f"CAPPL:FA[{unit}].betriebsart_fa"
        value = mode_map[mode]
        
        _LOGGER.info(f"Setting Pellematic {unit} mode to {mode} (value={value})")
        
        try:
            result = await api.set_data(parameter, value, divisor=None)
            _LOGGER.info(f"Service call successful: {result}")
        except Exception as e:
            _LOGGER.error(f"Service call failed: {e}")
            raise
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        handle_set_parameter,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_MODE,
        handle_set_system_mode,
        schema=SERVICE_SET_SYSTEM_MODE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEATING_MODE,
        handle_set_heating_mode,
        schema=SERVICE_SET_HEATING_MODE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HOT_WATER_MODE,
        handle_set_hot_water_mode,
        schema=SERVICE_SET_HOT_WATER_MODE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PELLEMATIC_MODE,
        handle_set_pellematic_mode,
        schema=SERVICE_SET_PELLEMATIC_MODE_SCHEMA,
    )
    
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