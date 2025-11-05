"""Platform for switch integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    # Get the coordinator from the sensor setup
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")
    api = hass.data[DOMAIN][config_entry.entry_id].get("api")
    device_name = config_entry.data.get("device_name", "ÖkOfen Pellematic")
    
    if not coordinator:
        _LOGGER.error("No coordinator found for switch setup")
        return
    
    entities = []
    
    # Add hot water mode switches
    if coordinator.data and 'hot_water' in coordinator.data:
        for hw in coordinator.data['hot_water']:
            entities.extend([
                PellematicHotWaterAutoModeSwitch(coordinator, config_entry, api, device_name, hw['index']),
                PellematicHotWaterOncePreparationSwitch(coordinator, config_entry, api, device_name, hw['index']),
            ])
    
    # Add heating circuit switches (if needed)
    # Note: Heating circuits are typically controlled via temperature setpoints rather than on/off switches
    
    async_add_entities(entities)


class PellematicHotWaterAutoModeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control hot water auto mode."""

    def __init__(self, coordinator, config_entry: ConfigEntry, api, device_name: str, hw_index: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._api = api
        self._device_name = device_name
        self._hw_index = hw_index
        self._attr_unique_id = f"{config_entry.entry_id}_hw_{hw_index}_auto_mode"
        self._attr_name = f"{device_name} HW {hw_index + 1} Auto Mode"
        self._attr_icon = "mdi:water-thermometer-outline"

    @property
    def is_on(self) -> bool | None:
        """Return true if hot water is in auto mode."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                # Mode "2" is typically auto mode
                mode = hw.get('betriebsart_numeric')
                return mode == 2
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                return {
                    "current_mode": hw.get('betriebsart_text', 'Unknown'),
                    "current_mode_numeric": hw.get('betriebsart_numeric', 'Unknown'),
                    "temp_heating": hw.get('temp_heizen'),
                    "temp_lowering": hw.get('temp_absenken'),
                }
        return {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn hot water auto mode on."""
        success = await self._api.set_hot_water_mode(self._hw_index, "2")  # "2" = Auto mode
        if success:
            _LOGGER.info(f"Successfully enabled auto mode for hot water {self._hw_index}")
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"Failed to enable auto mode for hot water {self._hw_index}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn hot water auto mode off (set to manual heating)."""
        success = await self._api.set_hot_water_mode(self._hw_index, "1")  # "1" = Manual heating mode
        if success:
            _LOGGER.info(f"Successfully disabled auto mode for hot water {self._hw_index}")
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"Failed to disable auto mode for hot water {self._hw_index}")


class PellematicHotWaterOncePreparationSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to trigger one-time hot water preparation."""

    def __init__(self, coordinator, config_entry: ConfigEntry, api, device_name: str, hw_index: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._api = api
        self._device_name = device_name
        self._hw_index = hw_index
        self._attr_unique_id = f"{config_entry.entry_id}_hw_{hw_index}_once_preparation"
        self._attr_name = f"{device_name} HW {hw_index + 1} Once Preparation"
        self._attr_icon = "mdi:water-plus"

    @property
    def is_on(self) -> bool | None:
        """Return true if one-time preparation is active."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                return hw.get('einmal_aufbereiten', False)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Trigger one-time hot water preparation."""
        parameter = f"CAPPL:LOCAL.ww[{self._hw_index}].einmal_aufbereiten"
        success = await self._api.set_parameter(parameter, "1")
        if success:
            _LOGGER.info(f"Successfully triggered once preparation for hot water {self._hw_index}")
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"Failed to trigger once preparation for hot water {self._hw_index}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Cancel one-time hot water preparation."""
        parameter = f"CAPPL:LOCAL.ww[{self._hw_index}].einmal_aufbereiten"
        success = await self._api.set_parameter(parameter, "0")
        if success:
            _LOGGER.info(f"Successfully cancelled once preparation for hot water {self._hw_index}")
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"Failed to cancel once preparation for hot water {self._hw_index}")


class PellematicPumpSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Pellematic Pump Switch."""

    def __init__(self, coordinator, config_entry: ConfigEntry, pump_index: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._pump_index = pump_index
        self._attr_unique_id = f"{config_entry.entry_id}_pump_{pump_index}"
        self._attr_name = f"ÖkOfen Pump {pump_index + 1}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the pump is on."""
        pumps = self.coordinator.data.get("pumps", [])
        for pump in pumps:
            if pump['index'] == self._pump_index:
                return pump.get('running', False)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pump on."""
        # Note: Pumps are typically controlled automatically by the heating system
        _LOGGER.warning("Direct pump control not recommended - pumps are controlled automatically by the heating system")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        # Note: Pumps are typically controlled automatically by the heating system  
        _LOGGER.warning("Direct pump control not recommended - pumps are controlled automatically by the heating system")