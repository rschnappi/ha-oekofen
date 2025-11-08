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

# Sensor definitions based on config.min.js JavaScript from ÖkOfen device
# Organized by device menu categories: Allgemein, Pellematic, Heizkreis, Warmwasser, Zubringerpumpe

SENSOR_DEFINITIONS = {
    # ========== BETRIEBSART (Operating Mode) ==========
    "system_mode": {
        "name": "System Operating Mode",
        "parameter": "CAPPL:LOCAL.anlage_betriebsart",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:cog",
        "category": "Betriebsart",
    },
    "hk1_mode": {
        "name": "HK1 Operating Mode",
        "parameter": "CAPPL:LOCAL.hk[0].betriebsart[0]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:cog",
        "category": "Betriebsart",
    },
    "ww1_mode": {
        "name": "Hot Water Operating Mode",
        "parameter": "CAPPL:LOCAL.ww[0].betriebsart[0]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:cog",
        "category": "Betriebsart",
    },
    "pellematic_mode": {
        "name": "Pellematic Operating Mode",
        "parameter": "CAPPL:FA[0].betriebsart_fa",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:cog",
        "category": "Betriebsart",
    },
    
    # ========== ALLGEMEIN (General) ==========
    "outside_temperature": {
        "name": "Outside Temperature",
        "parameter": "CAPPL:LOCAL.L_aussentemperatur_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "category": "Allgemein",
    },
    "software_version": {
        "name": "Software Version",
        "parameter": "CAPPL:LOCAL.touch[0].version",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:information",
        "category": "Allgemein",
        "entity_category": "diagnostic",
    },
    
    # ========== PELLEMATIC (Boiler) ==========
    "boiler_status": {
        "name": "Boiler Status",
        "parameter": "CAPPL:FA[0].L_kesselstatus",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:fire",
        "category": "Pellematic",
    },
    "boiler_temperature": {
        "name": "Boiler Temperature",
        "parameter": "CAPPL:FA[0].L_kesseltemperatur",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-high",
        "category": "Pellematic",
    },
    "boiler_target_temperature": {
        "name": "Boiler Target Temperature",
        "parameter": "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-high",
        "category": "Pellematic",
    },
    "exhaust_temperature": {
        "name": "Exhaust Temperature",
        "parameter": "CAPPL:FA[0].L_abgastemperatur",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-up",
        "category": "Pellematic",
    },
    "firebox_temperature": {
        "name": "Firebox Temperature",
        "parameter": "CAPPL:FA[0].L_feuerraumtemperatur",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:fire",
        "category": "Pellematic",
    },
    "firebox_target_temperature": {
        "name": "Firebox Target Temperature",
        "parameter": "CAPPL:FA[0].L_feuerraumtemperatur_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:fire",
        "category": "Pellematic",
    },
    
    # Pellet Feed System
    "feed_runtime": {
        "name": "Feed Runtime",
        "parameter": "CAPPL:FA[0].L_einschublaufzeit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "s",
        "icon": "mdi:timer",
        "category": "Pellematic",
    },
    "feed_pause": {
        "name": "Feed Pause",
        "parameter": "CAPPL:FA[0].L_pausenzeit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "s",
        "icon": "mdi:timer-pause",
        "category": "Pellematic",
    },
    
    # Fan and Suction System
    "fan_speed": {
        "name": "Fan Speed",
        "parameter": "CAPPL:FA[0].L_luefterdrehzahl",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:fan",
        "category": "Pellematic",
    },
    "exhaust_fan_speed": {
        "name": "Exhaust Fan Speed",
        "parameter": "CAPPL:FA[0].L_saugzugdrehzahl",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:fan",
        "category": "Pellematic",
    },
    "underpressure": {
        "name": "Underpressure",
        "parameter": "CAPPL:FA[0].L_unterdruck",
        "device_class": SensorDeviceClass.PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "Pa",
        "icon": "mdi:gauge",
        "category": "Pellematic",
    },
    "circulation_pump_speed": {
        "name": "Circulation Pump Speed",
        "parameter": "CAPPL:FA[0].L_drehzahl_uw_ist",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:pump",
        "category": "Pellematic",
    },
    
    # Status Sensors
    "burner_contact": {
        "name": "Burner Contact",
        "parameter": "CAPPL:FA[0].L_br1",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:fire-circle",
        "category": "Pellematic",
    },
    "hopper_sensor": {
        "name": "Hopper Sensor",
        "parameter": "CAPPL:FA[0].L_kap_sensor_raumentnahme",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:clipboard-check",
        "category": "Pellematic",
    },
    "intermediate_tank_sensor": {
        "name": "Intermediate Tank Sensor",
        "parameter": "CAPPL:FA[0].L_kap_sensor_zwischenbehaelter",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:clipboard-check",
        "category": "Pellematic",
    },
    "fire_damper": {
        "name": "Fire Damper",
        "parameter": "CAPPL:FA[0].L_bsk_status",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:valve",
        "category": "Pellematic",
    },
    
    # Pellet Fill Level
    "fill_level_current": {
        "name": "Pellet Fill Level",
        "parameter": "CAPPL:FA[0].L_fuellstand_aktuell",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "kg",
        "icon": "mdi:gauge",
        "category": "Pellematic",
    },
    "intermediate_tank_fill_level": {
        "name": "Intermediate Tank Fill Level",
        "parameter": "CAPPL:FA[0].L_zwischenbehaelter_aktuell",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "kg",
        "icon": "mdi:gauge",
        "category": "Pellematic",
    },
    "pellets_fill_percent": {
        "name": "Pellets Fill Percentage",
        "parameter": "CAPPL:FA[0].L_pelletsfuellstand",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:gauge",
        "category": "Pellematic",
    },
    
    # Ash Removal
    "ash_removal_speed": {
        "name": "Ash Removal Speed",
        "parameter": "CAPPL:FA[0].L_drehzahl_ascheschnecke_ist",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:delete-sweep",
        "category": "Pellematic",
    },
    
    # Statistics
    "burner_starts": {
        "name": "Burner Starts",
        "parameter": "CAPPL:FA[0].L_brennerstarts",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": None,
        "icon": "mdi:counter",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    "burner_runtime": {
        "name": "Burner Runtime",
        "parameter": "CAPPL:FA[0].L_brennerlaufzeit_anzeige",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": "h",
        "icon": "mdi:clock-time-eight",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    "average_runtime": {
        "name": "Average Runtime",
        "parameter": "CAPPL:FA[0].L_mittlere_laufzeit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "h",
        "icon": "mdi:clock-outline",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    "standby_time": {
        "name": "Standby Time",
        "parameter": "CAPPL:FA[0].L_sillstandszeit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "h",
        "icon": "mdi:clock-outline",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    "ignition_count": {
        "name": "Ignition Count",
        "parameter": "CAPPL:FA[0].L_anzahl_zuendung",
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": None,
        "icon": "mdi:counter",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    "suction_interval": {
        "name": "Suction Interval",
        "parameter": "CAPPL:FA[0].L_saugintervall",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "s",
        "icon": "mdi:timer",
        "category": "Pellematic",
    },
    
    # Motor Status
    "motor_suction_turbine": {
        "name": "Suction Turbine",
        "parameter": "CAPPL:FA[0].ausgang_motor[0]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:fan",
        "category": "Pellematic",
    },
    "motor_igniter": {
        "name": "Igniter",
        "parameter": "CAPPL:FA[0].ausgang_motor[1]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:electric-switch",
        "category": "Pellematic",
    },
    "motor_cleaning": {
        "name": "Cleaning Motor",
        "parameter": "CAPPL:FA[0].ausgang_motor[5]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:broom",
        "category": "Pellematic",
    },
    "motor_hopper_auger": {
        "name": "Hopper Auger",
        "parameter": "CAPPL:FA[0].ausgang_motor[8]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:screw-machine-round-top",
        "category": "Pellematic",
    },
    "motor_feed_auger": {
        "name": "Feed Auger",
        "parameter": "CAPPL:FA[0].ausgang_motor[11]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:screw-machine-round-top",
        "category": "Pellematic",
    },
    "motor_ash_removal": {
        "name": "Ash Removal Motor",
        "parameter": "CAPPL:FA[0].ausgang_motor[2]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:delete-sweep",
        "category": "Pellematic",
    },
    "magnet_valve": {
        "name": "Magnet Valve",
        "parameter": "CAPPL:FA[0].ausgang_motor[4]",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:valve",
        "category": "Pellematic",
    },
    "fault_relay": {
        "name": "Fault Relay",
        "parameter": "CAPPL:FA[0].ausgang_stoermelderelais",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:alert-circle",
        "category": "Pellematic",
        "entity_category": "diagnostic",
    },
    
    # ========== HEIZKREIS (Heating Circuit) ==========
    "hk1_flow_temperature": {
        "name": "HK1 Flow Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-lines",
        "category": "Heizkreis",
    },
    "hk1_flow_target_temperature": {
        "name": "HK1 Flow Target Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].vorlauftemp_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-lines",
        "category": "Heizkreis",
    },
    "hk1_room_temperature": {
        "name": "HK1 Room Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].raumtemp_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:home-thermometer",
        "category": "Heizkreis",
    },
    "hk1_room_target_temperature": {
        "name": "HK1 Room Target Temperature",
        "parameter": "CAPPL:LOCAL.L_hk[0].raumtemp_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:home-thermometer",
        "category": "Heizkreis",
    },
    "hk1_pump": {
        "name": "HK1 Pump",
        "parameter": "CAPPL:LOCAL.L_hk[0].pumpe",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:pump",
        "category": "Heizkreis",
    },
    
    # Heizkreis Settings (Einstellungen)
    "hk1_room_temp_heating": {
        "name": "HK1 Room Temp Heating",
        "parameter": "CAPPL:LOCAL.hk[0].raumtemp_heizen",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermostat",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_room_temp_lowering": {
        "name": "HK1 Room Temp Lowering",
        "parameter": "CAPPL:LOCAL.hk[0].raumtemp_absenken",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermostat",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_active_time_program": {
        "name": "HK1 Active Time Program",
        "parameter": "CAPPL:LOCAL.hk[0].aktives_zeitprogramm",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:clock-time-eight",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_heating_curve_slope": {
        "name": "HK1 Heating Curve Slope",
        "parameter": "CAPPL:LOCAL.hk[0].heizkurve_steigung",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,
        "icon": "mdi:chart-line",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_heating_curve_base": {
        "name": "HK1 Heating Curve Base",
        "parameter": "CAPPL:LOCAL.hk[0].heizkurve_fusspunkt",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:chart-line",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_heating_limit_heating": {
        "name": "HK1 Heating Limit Heating",
        "parameter": "CAPPL:LOCAL.hk[0].heizgrenze_heizen",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-down",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_heating_limit_lowering": {
        "name": "HK1 Heating Limit Lowering",
        "parameter": "CAPPL:LOCAL.hk[0].heizgrenze_absenken",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-down",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_room_sensor_influence": {
        "name": "HK1 Room Sensor Influence",
        "parameter": "CAPPL:LOCAL.hk[0].raumfuehler_einfluss",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:gauge",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_flow_temp_max": {
        "name": "HK1 Flow Temperature Maximum",
        "parameter": "CAPPL:LOCAL.hk[0].vorlauftemp_max",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-high",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    "hk1_flow_temp_min": {
        "name": "HK1 Flow Temperature Minimum",
        "parameter": "CAPPL:LOCAL.hk[0].vorlauftemp_min",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-low",
        "category": "Heizkreis",
        "entity_category": "config",
    },
    
    # ========== WARMWASSER (Hot Water) ==========
    "ww1_temperature": {
        "name": "Hot Water Temperature",
        "parameter": "CAPPL:LOCAL.L_ww[0].einschaltfuehler_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
        "category": "Warmwasser",
    },
    "ww1_target_temperature": {
        "name": "Hot Water Target Temperature",
        "parameter": "CAPPL:LOCAL.L_ww[0].temp_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
        "category": "Warmwasser",
    },
    "ww1_off_temperature": {
        "name": "Hot Water Off Temperature",
        "parameter": "CAPPL:LOCAL.L_ww[0].ausschaltfuehler_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
        "category": "Warmwasser",
    },
    "ww1_pump": {
        "name": "Hot Water Pump",
        "parameter": "CAPPL:LOCAL.L_ww[0].pumpe",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:pump",
        "category": "Warmwasser",
    },
    
    # Warmwasser Settings (Einstellungen)
    "ww1_temp_heating": {
        "name": "Hot Water Temp Heating",
        "parameter": "CAPPL:LOCAL.ww[0].temp_heizen",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_temp_lowering": {
        "name": "Hot Water Temp Lowering",
        "parameter": "CAPPL:LOCAL.ww[0].temp_absenken",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:water-thermometer",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_active_time_program": {
        "name": "Hot Water Active Time Program",
        "parameter": "CAPPL:LOCAL.ww[0].aktives_zeitprogramm",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:clock-time-eight",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_once_prepare": {
        "name": "Hot Water Once Prepare",
        "parameter": "CAPPL:LOCAL.ww[0].einmal_aufbereiten",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:water-plus",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_priority": {
        "name": "Hot Water Priority",
        "parameter": "CAPPL:LOCAL.ww[0].prioritaet",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:priority-high",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_overheat": {
        "name": "Hot Water Overheat",
        "parameter": "CAPPL:LOCAL.ww[0].ueberhoehung",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "K",
        "icon": "mdi:thermometer-plus",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_run_on_time": {
        "name": "Hot Water Run-On Time",
        "parameter": "CAPPL:LOCAL.ww[0].nachlaufzeit",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "min",
        "icon": "mdi:timer",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_switch_on_hysteresis": {
        "name": "Hot Water Switch-On Hysteresis",
        "parameter": "CAPPL:LOCAL.ww[0].hysterese",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "K",
        "icon": "mdi:gauge",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    "ww1_legionella_protection": {
        "name": "Hot Water Legionella Protection",
        "parameter": "CAPPL:LOCAL.ww[0].legionellen_wochentag",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:shield-check",
        "category": "Warmwasser",
        "entity_category": "config",
    },
    
    # ========== ZUBRINGERPUMPE (Supply Pump) ==========
    "supply_pump": {
        "name": "Supply Pump",
        "parameter": "CAPPL:LOCAL.L_zubrp[0].pumpe",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:pump",
        "category": "Zubringerpumpe",
    },
    
    # ========== PUFFER (Buffer) ==========
    "buffer_top_temperature": {
        "name": "Buffer Top Temperature",
        "parameter": "CAPPL:LOCAL.L_pu[0].einschaltfuehler_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "category": "Puffer",
    },
    "buffer_top_target_temperature": {
        "name": "Buffer Top Target Temperature",
        "parameter": "CAPPL:LOCAL.L_pu[0].einschaltfuehler_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "category": "Puffer",
    },
    "buffer_bottom_temperature": {
        "name": "Buffer Bottom Temperature",
        "parameter": "CAPPL:LOCAL.L_pu[0].ausschaltfuehler_ist",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "category": "Puffer",
    },
    "buffer_bottom_target_temperature": {
        "name": "Buffer Bottom Target Temperature",
        "parameter": "CAPPL:LOCAL.L_pu[0].ausschaltfuehler_soll",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "category": "Puffer",
    },
    "buffer_pump": {
        "name": "Buffer Pump",
        "parameter": "CAPPL:LOCAL.L_pu[0].pumpe",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:pump",
        "category": "Puffer",
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