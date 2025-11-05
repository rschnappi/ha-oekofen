"""Platform for sensor integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_LANGUAGE, CONF_INTERVAL, CONF_DEBUG_MODE
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    url = config_entry.data[CONF_URL]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    language = config_entry.data[CONF_LANGUAGE]
    interval = config_entry.data[CONF_INTERVAL]
    debug_mode = config_entry.data.get(CONF_DEBUG_MODE, False)
    
    api = PellematicAPI(url, username, password, language, debug_mode)
    coordinator = PellematicDataUpdateCoordinator(hass, api, interval)
    await coordinator.async_config_entry_first_refresh()

    entities = [
        PellematicOutsideTemperatureSensor(coordinator, config_entry),
        PellematicBufferTankTemperatureSensor(coordinator, config_entry),
        PellematicErrorCountSensor(coordinator, config_entry),
    ]
    
    # Add boiler sensors
    if coordinator.data and 'boilers' in coordinator.data:
        for boiler in coordinator.data['boilers']:
            entities.extend([
                PellematicBoilerTemperatureSensor(coordinator, config_entry, boiler['index']),
                PellematicBoilerStatusSensor(coordinator, config_entry, boiler['index']),
            ])
    
    async_add_entities(entities)


class PellematicDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Pellematic API."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, interval: int) -> None:
        """Initialize."""
        self.api = api
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.get_parsed_data()
            if data is None:
                raise UpdateFailed("Failed to fetch data from Pellematic system")
            return data
        except Exception as exception:
            raise UpdateFailed(exception) from exception
    
    async def async_shutdown(self) -> None:
        """Clean up resources."""
        await self.api.close()


class PellematicOutsideTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of outside temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_outside_temperature"
        self._attr_name = "ÖkOfen Outside Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("outside_temperature")


class PellematicBufferTankTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of buffer tank temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_buffer_tank_temperature"
        self._attr_name = "ÖkOfen Buffer Tank Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("buffer_tank_temperature")


class PellematicErrorCountSensor(CoordinatorEntity, SensorEntity):
    """Representation of error count sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_error_count"
        self._attr_name = "ÖkOfen Error Count"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("error_count")


class PellematicBoilerTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, boiler_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._boiler_index = boiler_index
        self._attr_unique_id = f"{config_entry.entry_id}_boiler_{boiler_index}_temperature"
        self._attr_name = f"ÖkOfen Boiler {boiler_index + 1} Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        boilers = self.coordinator.data.get("boilers", [])
        for boiler in boilers:
            if boiler['index'] == self._boiler_index:
                return boiler.get('temperature')
        return None


class PellematicBoilerStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler status sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, boiler_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._boiler_index = boiler_index
        self._attr_unique_id = f"{config_entry.entry_id}_boiler_{boiler_index}_status"
        self._attr_name = f"ÖkOfen Boiler {boiler_index + 1} Status"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        boilers = self.coordinator.data.get("boilers", [])
        for boiler in boilers:
            if boiler['index'] == self._boiler_index:
                return boiler.get('status')
        return None