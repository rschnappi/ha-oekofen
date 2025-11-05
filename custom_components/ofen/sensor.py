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
from homeassistant.const import UnitOfTemperature, UnitOfTime
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
        PellematicMaintenanceTimestampSensor(coordinator, config_entry, device_name),
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
    
    # Add heating circuit sensors
    if coordinator.data and 'heating_circuits' in coordinator.data:
        for hc in coordinator.data['heating_circuits']:
            entities.extend([
                PellematicHeatingCircuitModeSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitRoomTempActualSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitRoomTempTargetSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitRoomTempHeatingSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitRoomTempLoweringSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitFlowTempActualSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitFlowTempTargetSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitActiveProgramSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCircuitPumpSensor(coordinator, config_entry, device_name, hc['index']),
                # Heizkurven-Sensoren
                PellematicHeatingCurveSteigungSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingCurveFusspunktSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingLimitHeizenSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicHeatingLimitAbsenkenSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicVorhaltezeitSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicRoomSensorInfluenceSensor(coordinator, config_entry, device_name, hc['index']),
                PellematicRoomTempPlusSensor(coordinator, config_entry, device_name, hc['index']),
            ])
    
    # Add hot water sensors
    if coordinator.data and 'hot_water' in coordinator.data:
        for hw in coordinator.data['hot_water']:
            entities.extend([
                PellematicHotWaterOperatingModeSensor(coordinator, config_entry, device_name, hw['index']),
                PellematicHotWaterTempHeizenSensor(coordinator, config_entry, device_name, hw['index']),
                PellematicHotWaterTempAbsenkenSensor(coordinator, config_entry, device_name, hw['index']),
            ])
    
    # Add system sensors
    entities.extend([
        PellematicSystemErrorCountSensor(coordinator, config_entry, device_name),
        PellematicKesselStatusSensor(coordinator, config_entry, device_name),
        PellematicKesselTargetTempDisplaySensor(coordinator, config_entry, device_name),
        
        # Ash system sensors  
        PellematicAshScrewSpeedSensor(coordinator, config_entry, device_name),
        PellematicAshExternalBoxSensor(coordinator, config_entry, device_name),
        
        # Turbine and cleaning sensors
        PellematicTurbineVacuumCycleSensor(coordinator, config_entry, device_name),
        PellematicTurbineVacuumPauseSensor(coordinator, config_entry, device_name),
        PellematicTurbineSuctionIntervalSensor(coordinator, config_entry, device_name),
        
        # Extended temperature sensors
        PellematicExhaustTempAvailableSensor(coordinator, config_entry, device_name),
        PellematicFireboxTempAvailableSensor(coordinator, config_entry, device_name),
        PellematicFireboxTargetTempSensor(coordinator, config_entry, device_name),
        
        # Fan and operation sensors
        PellematicFanSpeedSensor(coordinator, config_entry, device_name),
        PellematicExhaustFanSpeedSensor(coordinator, config_entry, device_name),
        PellematicUnderpressureModeSensor(coordinator, config_entry, device_name),
        PellematicUnderpressureSensor(coordinator, config_entry, device_name),
        
        # Operation time sensors
        PellematicFeedRuntimeSensor(coordinator, config_entry, device_name),
        PellematicPauseTimeSensor(coordinator, config_entry, device_name),
        PellematicSuctionIntervalSensor(coordinator, config_entry, device_name),
    ])
    
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


class PellematicMaintenanceTimestampSensor(CoordinatorEntity, SensorEntity):
    """Representation of maintenance timestamp sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_maintenance_timestamp"
        self._attr_name = f"{device_name} Maintenance Timestamp"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        timestamp_data = self.coordinator.data.get("maintenance_timestamp")
        if isinstance(timestamp_data, dict):
            return timestamp_data.get('readable', timestamp_data.get('datetime'))
        return str(timestamp_data) if timestamp_data is not None else None


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


# Heating Circuit Sensors
class PellematicHeatingCircuitModeSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit mode sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_mode"
        self._attr_name = f"{device_name} Heating Circuit {hc_index + 1} Mode"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                mode_text = hc.get('mode_text')
                if mode_text:
                    return mode_text
                mode_numeric = hc.get('mode_numeric')
                return str(mode_numeric) if mode_numeric is not None else None
        return None


class PellematicHeatingCircuitRoomTempActualSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit room temperature actual sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_room_temp_actual"
        self._attr_name = f"{device_name} HC {hc_index + 1} Room Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('room_temp_actual')
        return None


class PellematicHeatingCircuitRoomTempTargetSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit room temperature target sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_room_temp_target"
        self._attr_name = f"{device_name} HC {hc_index + 1} Room Target Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('room_temp_target')
        return None


class PellematicHeatingCircuitRoomTempHeatingSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit room temperature heating setting sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_room_temp_heating"
        self._attr_name = f"{device_name} HC {hc_index + 1} Heating Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('room_temp_heating')
        return None


class PellematicHeatingCircuitRoomTempLoweringSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit room temperature lowering setting sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_room_temp_lowering"
        self._attr_name = f"{device_name} HC {hc_index + 1} Lowering Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('room_temp_lowering')
        return None


class PellematicHeatingCircuitFlowTempActualSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit flow temperature actual sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_flow_temp_actual"
        self._attr_name = f"{device_name} HC {hc_index + 1} Flow Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('flow_temp_actual')
        return None


class PellematicHeatingCircuitFlowTempTargetSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit flow temperature target sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_flow_temp_target"
        self._attr_name = f"{device_name} HC {hc_index + 1} Flow Target Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('flow_temp_target')
        return None


class PellematicHeatingCircuitActiveProgramSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit active program sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_active_program"
        self._attr_name = f"{device_name} HC {hc_index + 1} Active Program"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                program_text = hc.get('active_program_text')
                if program_text:
                    return program_text
                program_numeric = hc.get('active_program_numeric')
                return str(program_numeric) if program_numeric is not None else None
        return None


class PellematicHeatingCircuitPumpSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating circuit pump sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_pump"
        self._attr_name = f"{device_name} HC {hc_index + 1} Pump"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                pump_running = hc.get('pump_running')
                if pump_running is not None:
                    return "Running" if pump_running else "Stopped"
        return None


class PellematicHeatingCurveSteigungSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating curve slope sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_heizkurve_steigung"
        self._attr_name = f"{device_name} HC {hc_index + 1} Heizkurve Steigung"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('heizkurve_steigung')
        return None


class PellematicHeatingCurveFusspunktSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating curve base point sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_heizkurve_fusspunkt"
        self._attr_name = f"{device_name} HC {hc_index + 1} Heizkurve Fußpunkt"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('heizkurve_fusspunkt')
        return None


class PellematicHeatingLimitHeizenSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating limit sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_heizgrenze_heizen"
        self._attr_name = f"{device_name} HC {hc_index + 1} Heizgrenze Heizen"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-high"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('heizgrenze_heizen')
        return None


class PellematicHeatingLimitAbsenkenSensor(CoordinatorEntity, SensorEntity):
    """Representation of heating limit lowering sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_heizgrenze_absenken"
        self._attr_name = f"{device_name} HC {hc_index + 1} Heizgrenze Absenken"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-low"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('heizgrenze_absenken')
        return None


class PellematicVorhaltezeitSensor(CoordinatorEntity, SensorEntity):
    """Representation of lead time sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_vorhaltezeit"
        self._attr_name = f"{device_name} HC {hc_index + 1} Vorhaltezeit"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('vorhaltezeit')
        return None


class PellematicRoomSensorInfluenceSensor(CoordinatorEntity, SensorEntity):
    """Representation of room sensor influence sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_raumfuehler_einfluss"
        self._attr_name = f"{device_name} HC {hc_index + 1} Raumfühler Einfluss"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('raumfuehler_einfluss')
        return None


class PellematicRoomTempPlusSensor(CoordinatorEntity, SensorEntity):
    """Representation of room temperature plus adjustment sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hc_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hc_index = hc_index
        self._attr_unique_id = f"{config_entry.entry_id}_hc_{hc_index}_raumtemp_plus"
        self._attr_name = f"{device_name} HC {hc_index + 1} Raumtemp Plus"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "K"
        self._attr_icon = "mdi:thermometer-plus"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        heating_circuits = self.coordinator.data.get("heating_circuits", [])
        for hc in heating_circuits:
            if hc['index'] == self._hc_index:
                return hc.get('raumtemp_plus')
        return None


# Hot Water Sensors
class PellematicHotWaterOperatingModeSensor(CoordinatorEntity, SensorEntity):
    """Representation of hot water operating mode sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hw_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hw_index = hw_index
        self._attr_unique_id = f"{config_entry.entry_id}_hw_{hw_index}_operating_mode"
        self._attr_name = f"{device_name} HW {hw_index + 1} Betriebsart"
        self._attr_icon = "mdi:water-thermometer"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                return hw.get('betriebsart_text') or str(hw.get('betriebsart_numeric', ''))
        return None


class PellematicHotWaterTempHeizenSensor(CoordinatorEntity, SensorEntity):
    """Representation of hot water heating temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hw_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hw_index = hw_index
        self._attr_unique_id = f"{config_entry.entry_id}_hw_{hw_index}_temp_heizen"
        self._attr_name = f"{device_name} HW {hw_index + 1} Temp Heizen"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                return hw.get('temp_heizen')
        return None


class PellematicHotWaterTempAbsenkenSensor(CoordinatorEntity, SensorEntity):
    """Representation of hot water lowering temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str, hw_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._hw_index = hw_index
        self._attr_unique_id = f"{config_entry.entry_id}_hw_{hw_index}_temp_absenken"
        self._attr_name = f"{device_name} HW {hw_index + 1} Temp Absenken"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        hot_water = self.coordinator.data.get("hot_water", [])
        for hw in hot_water:
            if hw['index'] == self._hw_index:
                return hw.get('temp_absenken')
        return None


# System Status Sensors
class PellematicSystemErrorCountSensor(CoordinatorEntity, SensorEntity):
    """Representation of system error count sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_system_error_count"
        self._attr_name = f"{device_name} System Error Count"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:alert-circle"

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_zaehler_fehler")


class PellematicKesselStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler status sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_kessel_status"
        self._attr_name = f"{device_name} Kessel Status"
        self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_kesselstatus")


class PellematicKesselTargetTempDisplaySensor(CoordinatorEntity, SensorEntity):
    """Representation of boiler target temperature display sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_kessel_target_temp_display"
        self._attr_name = f"{device_name} Kessel Soll Temperatur Anzeige"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_kesseltemperatur_soll_anzeige")


# Ash System Sensors
class PellematicAshScrewSpeedSensor(CoordinatorEntity, SensorEntity):
    """Representation of ash screw speed sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_ash_screw_speed"
        self._attr_name = f"{device_name} Ascheschnecke Drehzahl"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "rpm"
        self._attr_icon = "mdi:rotate-right"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_drehzahl_ascheschnecke_ist")


class PellematicAshExternalBoxSensor(CoordinatorEntity, SensorEntity):
    """Representation of external ash box sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_ash_external_box"
        self._attr_name = f"{device_name} Externe Aschebox"
        self._attr_icon = "mdi:delete"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        value = self.coordinator.data.get("asche_externe_aschebox")
        return "Enabled" if value else "Disabled" if value is not None else None


# Turbine and Cleaning Sensors
class PellematicTurbineVacuumCycleSensor(CoordinatorEntity, SensorEntity):
    """Representation of turbine vacuum cycle sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_turbine_vacuum_cycle"
        self._attr_name = f"{device_name} Turbine Vacuum Takt"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("turbine_takt_ra_vacuum")


class PellematicTurbineVacuumPauseSensor(CoordinatorEntity, SensorEntity):
    """Representation of turbine vacuum pause sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_turbine_vacuum_pause"
        self._attr_name = f"{device_name} Turbine Vacuum Pause"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("turbine_pause_ra_vacuum")


class PellematicTurbineSuctionIntervalSensor(CoordinatorEntity, SensorEntity):
    """Representation of turbine suction interval sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_turbine_suction_interval"
        self._attr_name = f"{device_name} Turbine Saugintervall"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("turbine_saugintervall")


# Extended Temperature Sensors
class PellematicExhaustTempAvailableSensor(CoordinatorEntity, SensorEntity):
    """Representation of exhaust temperature availability sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_exhaust_temp_available"
        self._attr_name = f"{device_name} Abgastemperatur verfügbar"
        self._attr_icon = "mdi:check-circle"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        value = self.coordinator.data.get("L_abgastemperatur_vorhanden")
        return "Available" if value else "Not Available" if value is not None else None


class PellematicFireboxTempAvailableSensor(CoordinatorEntity, SensorEntity):
    """Representation of firebox temperature availability sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_firebox_temp_available"
        self._attr_name = f"{device_name} Feuerraumtemperatur verfügbar"
        self._attr_icon = "mdi:check-circle"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        value = self.coordinator.data.get("L_feuerraumtemperatur_vorhanden")
        return "Available" if value else "Not Available" if value is not None else None


class PellematicFireboxTargetTempSensor(CoordinatorEntity, SensorEntity):
    """Representation of firebox target temperature sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_firebox_target_temp"
        self._attr_name = f"{device_name} Feuerraum Soll Temperatur"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_feuerraumtemperatur_soll")


# Fan and Operation Sensors
class PellematicFanSpeedSensor(CoordinatorEntity, SensorEntity):
    """Representation of fan speed sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_fan_speed"
        self._attr_name = f"{device_name} Lüfter Drehzahl"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "rpm"
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_luefterdrehzahl")


class PellematicExhaustFanSpeedSensor(CoordinatorEntity, SensorEntity):
    """Representation of exhaust fan speed sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_exhaust_fan_speed"
        self._attr_name = f"{device_name} Saugzug Drehzahl"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "rpm"
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_saugzugdrehzahl")


class PellematicUnderpressureModeSensor(CoordinatorEntity, SensorEntity):
    """Representation of underpressure mode sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_underpressure_mode"
        self._attr_name = f"{device_name} Unterdruck Modus"
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("unterdruck_modus")


class PellematicUnderpressureSensor(CoordinatorEntity, SensorEntity):
    """Representation of underpressure sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_underpressure"
        self._attr_name = f"{device_name} Unterdruck"
        self._attr_device_class = SensorDeviceClass.PRESSURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "Pa"
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_unterdruck")


# Operation Time Sensors
class PellematicFeedRuntimeSensor(CoordinatorEntity, SensorEntity):
    """Representation of feed runtime sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_feed_runtime"
        self._attr_name = f"{device_name} Einschub Laufzeit"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_einschublaufzeit")


class PellematicPauseTimeSensor(CoordinatorEntity, SensorEntity):
    """Representation of pause time sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_pause_time"
        self._attr_name = f"{device_name} Pausenzeit"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_pausenzeit")


class PellematicSuctionIntervalSensor(CoordinatorEntity, SensorEntity):
    """Representation of suction interval sensor."""

    def __init__(self, coordinator: PellematicDataUpdateCoordinator, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_suction_interval"
        self._attr_name = f"{device_name} Saugintervall"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:clock"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("L_saugintervall")