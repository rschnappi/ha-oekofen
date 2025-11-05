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
    
    if not coordinator:
        _LOGGER.error("No coordinator found for switch setup")
        return
    
    entities = []
    
    # Add pump switches based on available pumps
    if coordinator.data and 'pumps' in coordinator.data:
        for pump in coordinator.data['pumps']:
            entities.append(PellematicPumpSwitch(coordinator, config_entry, pump['index']))
    
    async_add_entities(entities)


class PellematicPumpSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Pellematic Pump Switch."""

    def __init__(self, coordinator, config_entry: ConfigEntry, pump_index: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._pump_index = pump_index
        self._attr_unique_id = f"{config_entry.entry_id}_pump_{pump_index}"
        self._attr_name = f"Pump {pump_index + 1}"

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
        # TODO: Implement pump control API call
        # This would require additional API endpoints that may not be available
        # in the Pellematic system for direct pump control
        _LOGGER.warning("Pump control not implemented - pumps are typically controlled automatically by the heating system")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        # TODO: Implement pump control API call
        _LOGGER.warning("Pump control not implemented - pumps are typically controlled automatically by the heating system")