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

from .const import DOMAIN, CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_LANGUAGE, CONF_INTERVAL, CONF_DEBUG_MODE, CONF_DEVICE_NAME
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
    device_name = config_entry.data.get(CONF_DEVICE_NAME, "ÖkOfen")

    api = PellematicAPI(url, username, password, language, debug_mode)
    coordinator = PellematicDataUpdateCoordinator(hass, api, interval)
    await coordinator.async_config_entry_first_refresh()

    entities = [
        PellematicOutsideTemperatureSensor(coordinator, config_entry, device_name),
        PellematicBufferTankTemperatureSensor(coordinator, config_entry, device_name),
        PellematicErrorCountSensor(coordinator, config_entry, device_name),
        PellematicSystemModeSensor(coordinator, config_entry, device_name),
    ]

    # Add boiler sensors
    if coordinator.data and 'boilers' in coordinator.data:
        for boiler in coordinator.data['boilers']:
            entities.extend([
                PellematicBoilerTemperatureSensor(coordinator, config_entry, device_name, boiler['index']),
                PellematicBoilerStatusSensor(coordinator, config_entry, device_name, boiler['index']),
                PellematicBoilerTargetTemperatureSensor(coordinator, config_entry, device_name, boiler['index']),
            ])

    # Add pump sensors
    if coordinator.data and 'pumps' in coordinator.data:
        for pump in coordinator.data['pumps']:
            entities.append(
                PellematicPumpSensor(coordinator, config_entry, device_name, pump['index'])
            )
    
    # Add additional sensors for all raw data points if in debug mode
    if debug_mode and coordinator.data and 'raw_data' in coordinator.data:
        for param_name, value in coordinator.data['raw_data'].items():
            # Skip parameters we already have specific sensors for
            if not any(skip in param_name for skip in [
                'L_aussentemperatur_ist', 'L_bestke_temp_ist', 'L_zaehler_fehler',
                'anlage_betriebsart', 'L_kesselstatus', 'L_kesseltemperatur', 
                'L_pu', 'pumpe'
            ]):
                entities.append(
                    PellematicGenericSensor(coordinator, config_entry, device_name, param_name, value)
                )

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

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_outside_temperature"
        self._attr_name = f"{device_name} Outside Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("outside_temperature")


class PellematicBufferTankTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of buffer tank temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_buffer_tank_temperature"
        self._attr_name = f"{device_name} Buffer Tank Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("buffer_tank_temperature")


class PellematicErrorCountSensor(CoordinatorEntity, SensorEntity):
    """Representation of error count sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_error_count"
        self._attr_name = f"{device_name} Error Count"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("error_count")


class PellematicBoilerTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, boiler_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._boiler_index = boiler_index
        self._attr_unique_id = f"{config_entry.entry_id}_boiler_{boiler_index}_temperature"
        self._attr_name = f"{device_name} Boiler {boiler_index + 1} Temperature"
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

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, boiler_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._boiler_index = boiler_index
        self._attr_unique_id = f"{config_entry.entry_id}_boiler_{boiler_index}_status"
        self._attr_name = f"{device_name} Boiler {boiler_index + 1} Status"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        boilers = self.coordinator.data.get("boilers", [])
        for boiler in boilers:
            if boiler['index'] == self._boiler_index:
                # Try to get the text value first, fallback to numeric
                status_text = boiler.get('status_text')
                if status_text:
                    return status_text
                
                status_numeric = boiler.get('status_numeric')
                if status_numeric is not None:
                    return str(status_numeric)
                
                # Fallback to old format for compatibility
                old_status = boiler.get('status')
                if isinstance(old_status, dict):
                    return old_status.get('text_value', str(old_status.get('numeric_value', 'Unknown')))
                elif old_status is not None:
                    return str(old_status)
        return None


class PellematicSystemModeSensor(CoordinatorEntity, SensorEntity):
    """Representation of system mode sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_system_mode"
        self._attr_name = f"{device_name} System Mode"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        system_mode = self.coordinator.data.get("system_mode")
        if isinstance(system_mode, dict):
            return system_mode.get('text_value', str(system_mode.get('numeric_value', 'Unknown')))
        return str(system_mode) if system_mode is not None else None


class PellematicBoilerTargetTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler target temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, boiler_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._boiler_index = boiler_index
        self._attr_unique_id = f"{config_entry.entry_id}_boiler_{boiler_index}_target_temperature"
        self._attr_name = f"{device_name} Boiler {boiler_index + 1} Target Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        boilers = self.coordinator.data.get("boilers", [])
        for boiler in boilers:
            if boiler['index'] == self._boiler_index:
                return boiler.get('target_temperature')
        return None


class PellematicPumpSensor(CoordinatorEntity, SensorEntity):
    """Representation of pump sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, pump_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._pump_index = pump_index
        self._attr_unique_id = f"{config_entry.entry_id}_pump_{pump_index}"
        self._attr_name = f"{device_name} Pump {pump_index + 1}"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        pumps = self.coordinator.data.get("pumps", [])
        for pump in pumps:
            if pump['index'] == self._pump_index:
                return "Running" if pump.get('running') else "Stopped"
        return None


class PellematicGenericSensor(CoordinatorEntity, SensorEntity):
    """Representation of a generic parameter sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, param_name: str, value) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._param_name = param_name
        self._attr_unique_id = f"{config_entry.entry_id}_param_{param_name.replace(':', '_').replace('[', '_').replace(']', '_').replace('.', '_')}"
        
        # Create a friendly name from parameter name
        friendly_name = param_name.replace('CAPPL:', '').replace('LOCAL.', '').replace('FA[', 'Boiler_').replace('].', '_')
        self._attr_name = f"{device_name} {friendly_name}"
        
        # Set device class based on parameter name
        if 'temperatur' in param_name.lower() or 'temp' in param_name.lower():
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> str | float | None:
        """Return the native value of the sensor."""
        raw_data = self.coordinator.data.get("raw_data", {})
        value = raw_data.get(self._param_name)
        
        if isinstance(value, dict):
            # Handle structured values
            if 'text_value' in value:
                return value['text_value']
            elif 'readable' in value:  # Timestamp
                return value['readable']
            elif 'numeric_value' in value:
                return value['numeric_value']
        
        return value