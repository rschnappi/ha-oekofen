"""ÖkOfen Integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
]

# Service schemas
SET_PARAMETER_SCHEMA = vol.Schema({
    vol.Required("parameter"): cv.string,
    vol.Required("value"): cv.string,
})

SET_HOT_WATER_MODE_SCHEMA = vol.Schema({
    vol.Optional("hw_index", default=0): cv.positive_int,
    vol.Required("mode"): vol.In(["0", "1", "2"]),
})

SET_HEATING_CIRCUIT_MODE_SCHEMA = vol.Schema({
    vol.Optional("hc_index", default=0): cv.positive_int,
    vol.Required("mode"): cv.string,
})

SET_ROOM_TEMPERATURE_SCHEMA = vol.Schema({
    vol.Optional("hc_index", default=0): cv.positive_int,
    vol.Required("temperature"): vol.Coerce(float),
})

SET_HOT_WATER_TEMPERATURE_SCHEMA = vol.Schema({
    vol.Optional("hw_index", default=0): cv.positive_int,
    vol.Required("temp_type"): vol.In(["heizen", "absenken"]),
    vol.Required("temperature"): vol.Coerce(float),
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ÖkOfen component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ÖkOfen from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store entry data and API instance for easy access by platforms
    api = PellematicAPI(
        url=entry.data.get("url"),
        username=entry.data.get("username", ""),
        password=entry.data.get("password"),
        language=entry.data.get("language", "de"),
        debug_mode=entry.data.get("debug_mode", False)
    )
    
    hass.data[DOMAIN][entry.entry_id] = {
        "url": entry.data.get("url"),
        "username": entry.data.get("username"),
        "password": entry.data.get("password"),
        "language": entry.data.get("language"),
        "interval": entry.data.get("interval"),
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services only once
    if not hass.services.has_service(DOMAIN, "set_parameter"):
        _register_services(hass)
    
    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register ÖkOfen services."""
    
    async def handle_set_parameter(call: ServiceCall) -> None:
        """Handle set parameter service call."""
        parameter = call.data["parameter"]
        value = call.data["value"]
        
        # Get the first available API instance
        for entry_data in hass.data[DOMAIN].values():
            if "api" in entry_data:
                api = entry_data["api"]
                success = await api.set_parameter(parameter, value)
                if success:
                    _LOGGER.info(f"Successfully set {parameter} = {value}")
                else:
                    _LOGGER.error(f"Failed to set {parameter} = {value}")
                break
    
    async def handle_set_hot_water_mode(call: ServiceCall) -> None:
        """Handle set hot water mode service call."""
        hw_index = call.data["hw_index"]
        mode = call.data["mode"]
        
        for entry_data in hass.data[DOMAIN].values():
            if "api" in entry_data:
                api = entry_data["api"]
                success = await api.set_hot_water_mode(hw_index, mode)
                if success:
                    _LOGGER.info(f"Successfully set hot water {hw_index} mode to {mode}")
                else:
                    _LOGGER.error(f"Failed to set hot water {hw_index} mode to {mode}")
                break
    
    async def handle_set_heating_circuit_mode(call: ServiceCall) -> None:
        """Handle set heating circuit mode service call."""
        hc_index = call.data["hc_index"]
        mode = call.data["mode"]
        
        for entry_data in hass.data[DOMAIN].values():
            if "api" in entry_data:
                api = entry_data["api"]
                success = await api.set_heating_circuit_mode(hc_index, mode)
                if success:
                    _LOGGER.info(f"Successfully set heating circuit {hc_index} mode to {mode}")
                else:
                    _LOGGER.error(f"Failed to set heating circuit {hc_index} mode to {mode}")
                break
    
    async def handle_set_room_temperature(call: ServiceCall) -> None:
        """Handle set room temperature service call."""
        hc_index = call.data["hc_index"]
        temperature = call.data["temperature"]
        
        for entry_data in hass.data[DOMAIN].values():
            if "api" in entry_data:
                api = entry_data["api"]
                success = await api.set_room_temperature(hc_index, temperature)
                if success:
                    _LOGGER.info(f"Successfully set room temperature {hc_index} to {temperature}°C")
                else:
                    _LOGGER.error(f"Failed to set room temperature {hc_index} to {temperature}°C")
                break
    
    async def handle_set_hot_water_temperature(call: ServiceCall) -> None:
        """Handle set hot water temperature service call."""
        hw_index = call.data["hw_index"]
        temp_type = call.data["temp_type"]
        temperature = call.data["temperature"]
        
        for entry_data in hass.data[DOMAIN].values():
            if "api" in entry_data:
                api = entry_data["api"]
                success = await api.set_hot_water_temperature(hw_index, temp_type, temperature)
                if success:
                    _LOGGER.info(f"Successfully set hot water {hw_index} {temp_type} temperature to {temperature}°C")
                else:
                    _LOGGER.error(f"Failed to set hot water {hw_index} {temp_type} temperature to {temperature}°C")
                break
    
    # Register all services
    hass.services.async_register(
        DOMAIN, "set_parameter", handle_set_parameter, schema=SET_PARAMETER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_hot_water_mode", handle_set_hot_water_mode, schema=SET_HOT_WATER_MODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_heating_circuit_mode", handle_set_heating_circuit_mode, schema=SET_HEATING_CIRCUIT_MODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_room_temperature", handle_set_room_temperature, schema=SET_ROOM_TEMPERATURE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "set_hot_water_temperature", handle_set_hot_water_temperature, schema=SET_HOT_WATER_TEMPERATURE_SCHEMA
    )
    
    _LOGGER.info("ÖkOfen services registered successfully")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok