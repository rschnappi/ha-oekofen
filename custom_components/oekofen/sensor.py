"""Sensor platform for ÖkOfen Pellematic integration."""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    CONF_HOST,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.config_entries import ConfigEntry

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # Based on 5-second jQuery intervals, but more conservative

# Sensor definitions based on successful parameter testing
SENSOR_DEFINITIONS = {
    "outside_temperature": {
        "name": "Outside Temperature",
        "parameter": "CAPPL:LOCAL.L_aussentemperatur_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
    },
    "boiler_status": {
        "name": "Boiler Status",
        "parameter": "CAPPL:FA[0].L_kesselstatus",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:fire",
    },
    "boiler_temperature": {
        "name": "Boiler Temperature",
        "parameter": "CAPPL:FA[0].L_kesseltemperatur",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-high",
    },
    "boiler_target_temperature": {
        "name": "Boiler Target Temperature",
        "parameter": "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-high",
    },
    "exhaust_temperature": {
        "name": "Exhaust Temperature",
        "parameter": "CAPPL:FA[0].L_abgastemperatur",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-up",
    },
    "room_temperature": {
        "name": "Room Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].raumtemp_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:home-thermometer",
    },
    "flow_temperature": {
        "name": "Flow Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-lines",
    },
    "hot_water_temperature": {
        "name": "Hot Water Temperature",
        "parameter": "CAPPL:LOCAL.L_ww[0].temp_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ÖkOfen sensors from a config entry."""
    
    # Get the API instance from the integration data
    api = hass.data["oekofen"][config_entry.entry_id]["api"]
    
    # Create data update coordinator
    coordinator = OekofenDataUpdateCoordinator(hass, api)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create sensor entities
    entities = []
    for sensor_key, sensor_config in SENSOR_DEFINITIONS.items():
        entities.append(
            OekofenSensor(
                coordinator=coordinator,
                sensor_key=sensor_key,
                sensor_config=sensor_config,
                device_name=f"ÖkOfen {config_entry.data[CONF_HOST]}",
            )
        )
    
    async_add_entities(entities)


class OekofenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ÖkOfen API."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI) -> None:
        """Initialize the coordinator."""
        self.api = api
        
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Pellematic",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the ÖkOfen device."""
        try:
            # Get all parameters for defined sensors
            parameters = [config["parameter"] for config in SENSOR_DEFINITIONS.values()]
            data = await self.api.get_data(parameters)
            
            _LOGGER.debug(f"Updated data for {len(data)} parameters")
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}")


class OekofenSensor(CoordinatorEntity, SensorEntity):
    """Representation of an ÖkOfen sensor."""

    def __init__(
        self,
        coordinator: OekofenDataUpdateCoordinator,
        sensor_key: str,
        sensor_config: Dict[str, Any],
        device_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_key = sensor_key
        self._sensor_config = sensor_config
        self._device_name = device_name
        
        # Entity properties
        self._attr_name = sensor_config["name"]
        self._attr_unique_id = f"oekofen_{sensor_key}"
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")
        
        # Device info
        self._attr_device_info = {
            "identifiers": {("oekofen", device_name)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        parameter = self._sensor_config["parameter"]
        
        if parameter in self.coordinator.data:
            data_point = self.coordinator.data[parameter]
            value = data_point.get("value")
            divisor = data_point.get("divisor", "")
            format_texts = data_point.get("formatTexts", "")
            
            if value is None or value == "":
                return None
            
            try:
                # Check if this is an enum value (has formatTexts)
                if format_texts and format_texts != "":
                    # Split formatTexts by pipe
                    text_options = format_texts.split("|")
                    value_int = int(value)
                    
                    # Get the text at the index (value)
                    if 0 <= value_int < len(text_options):
                        return text_options[value_int]
                    else:
                        _LOGGER.warning(f"Value {value_int} out of range for formatTexts (0-{len(text_options)-1})")
                        return value
                
                # Check if this is a numeric value with divisor
                if divisor and divisor != "" and divisor != "0":
                    try:
                        divisor_float = float(divisor)
                        value_float = float(value)
                        result = value_float / divisor_float
                        
                        # Round to appropriate decimal places
                        if result.is_integer():
                            return int(result)
                        else:
                            return round(result, 1)
                    except (ValueError, ZeroDivisionError):
                        pass
                
                # For temperature sensors, convert to float
                if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                    return float(value)
                
                # Try to return as number if possible
                try:
                    value_float = float(value)
                    if value_float.is_integer():
                        return int(value_float)
                    return value_float
                except ValueError:
                    pass
                
                return value
                
            except (ValueError, TypeError) as e:
                _LOGGER.warning(f"Error processing value for {parameter}: {e}")
                return value
        
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        parameter = self._sensor_config["parameter"]
        
        if not self.coordinator.last_update_success:
            return False
            
        if parameter in self.coordinator.data:
            data_point = self.coordinator.data[parameter]
            return data_point.get("status") == "OK"
        
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        parameter = self._sensor_config["parameter"]
        attributes = {}
        
        if parameter in self.coordinator.data:
            data_point = self.coordinator.data[parameter]
            attributes["parameter"] = parameter
            attributes["status"] = data_point.get("status", "unknown")
            
            # Add original raw value
            raw_value = data_point.get("value")
            if raw_value:
                attributes["raw_value"] = raw_value
            
            # Add divisor if present
            divisor = data_point.get("divisor")
            if divisor and divisor != "":
                attributes["divisor"] = divisor
            
            # Add unit text
            unit_text = data_point.get("unitText")
            if unit_text and unit_text not in ["???", ""]:
                attributes["unit_from_device"] = unit_text
            
            # Add limits if present
            lower_limit = data_point.get("lowerLimit")
            if lower_limit and lower_limit != "":
                attributes["lower_limit"] = lower_limit
                
            upper_limit = data_point.get("upperLimit")
            if upper_limit and upper_limit != "":
                attributes["upper_limit"] = upper_limit
            
        return attributes