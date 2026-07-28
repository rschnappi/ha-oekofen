"""Number platform for ÖkOfen writable setpoints.

Parameter names and which ones are safely writable without entering the
installer code were taken from the vendor's own config.min.js (the same
JavaScript that drives the device's built-in web interface). Limits and
divisors are read live from the device's own response for each
parameter (lowerLimit/upperLimit/divisor) rather than hard-coded, since
that's exactly what the vendor UI itself does.
"""
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=60)


def build_number_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build the writable-number definitions for the circuits present on this device."""
    defs: Dict[str, Dict[str, Any]] = {}

    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_raumtemp_heizen"] = {
            "parameter": f"{base}.raumtemp_heizen",
            "name": f"{label} Raumtemp Heizen",
            "icon": "mdi:thermometer",
            "temperature": True,
        }
        defs[f"hk{idx}_raumtemp_absenken"] = {
            "parameter": f"{base}.raumtemp_absenken",
            "name": f"{label} Raumtemp Absenken",
            "icon": "mdi:thermometer-low",
            "temperature": True,
        }
        defs[f"hk{idx}_heizkurve_steigung"] = {
            "parameter": f"{base}.heizkurve_steigung",
            "name": f"{label} Heizkurve Steigung",
            "icon": "mdi:chart-line",
        }
        defs[f"hk{idx}_heizkurve_fusspunkt"] = {
            "parameter": f"{base}.heizkurve_fusspunkt",
            "name": f"{label} Heizkurve Fußpunkt",
            "icon": "mdi:chart-line",
            "temperature": True,
        }
        defs[f"hk{idx}_heizgrenze_heizen"] = {
            "parameter": f"{base}.heizgrenze_heizen",
            "name": f"{label} Heizgrenze Heizen",
            "icon": "mdi:thermometer-chevron-down",
            "temperature": True,
        }
        defs[f"hk{idx}_heizgrenze_absenken"] = {
            "parameter": f"{base}.heizgrenze_absenken",
            "name": f"{label} Heizgrenze Absenken",
            "icon": "mdi:thermometer-chevron-down",
            "temperature": True,
        }
        defs[f"hk{idx}_vorhaltezeit"] = {
            "parameter": f"{base}.vorhaltezeit",
            "name": f"{label} Vorhaltezeit",
            "icon": "mdi:timer-outline",
        }
        defs[f"hk{idx}_raumfuehlereinfluss"] = {
            "parameter": f"{base}.raumfuehler_einfluss",
            "name": f"{label} Raumfühlereinfluss",
            "icon": "mdi:percent-outline",
        }
        defs[f"hk{idx}_raumtemp_hysterese"] = {
            "parameter": f"{base}.raumtemp_plus",
            "name": f"{label} Raumtemp Hysterese",
            "icon": "mdi:thermometer",
        }

    for idx in circuits.get("ww", []):
        base = f"CAPPL:LOCAL.ww[{idx}]"
        label = f"Warmwasser {idx + 1}"
        defs[f"ww{idx}_wassertemp_soll"] = {
            "parameter": f"{base}.temp_heizen",
            "name": f"{label} Solltemperatur",
            "icon": "mdi:water-thermometer",
            "temperature": True,
        }
        defs[f"ww{idx}_wassertemp_min"] = {
            "parameter": f"{base}.temp_absenken",
            "name": f"{label} Minimaltemperatur",
            "icon": "mdi:water-thermometer-outline",
            "temperature": True,
        }

    for idx in circuits.get("zirkp", []):
        base = f"CAPPL:LOCAL.zirkp[{idx}]"
        label = f"Zirkulationspumpe {idx + 1}"
        defs[f"zirkp{idx}_abschalttemp"] = {
            "parameter": f"{base}.ruecklauftemp_soll",
            "name": f"{label} Abschalttemperatur",
            "icon": "mdi:water-thermometer",
            "temperature": True,
        }
        defs[f"zirkp{idx}_einschalthyst"] = {
            "parameter": f"{base}.hysterese",
            "name": f"{label} Einschalthysterese",
            "icon": "mdi:thermometer",
        }

    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable number entities for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    definitions = build_number_definitions(circuits)

    if not definitions:
        return

    parameters = [config["parameter"] for config in definitions.values()]
    coordinator = OekofenNumberCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenNumber(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenNumberCoordinator(DataUpdateCoordinator):
    """Coordinator polling the writable setpoint values."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: List[str]) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Sollwerte",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenNumber(CoordinatorEntity, NumberEntity):
    """A writable ÖkOfen setpoint, with limits/divisor read from the device itself."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OekofenNumberCoordinator,
        api: PellematicAPI,
        key: str,
        config: Dict[str, Any],
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._parameter = config["parameter"]
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = config.get("icon")
        if config.get("temperature"):
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._parameter)

    def _divisor(self) -> float:
        point = self._data_point()
        if not point:
            return 1.0
        try:
            divisor = float(point.get("divisor") or 1)
            return divisor if divisor > 0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    @property
    def native_value(self) -> Optional[float]:
        point = self._data_point()
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return round(float(point["value"]) / self._divisor(), 2)
        except (TypeError, ValueError):
            return None

    @property
    def native_min_value(self) -> float:
        point = self._data_point()
        if point:
            try:
                return round(float(point.get("lowerLimit")) / self._divisor(), 2)
            except (TypeError, ValueError):
                pass
        return -50.0

    @property
    def native_max_value(self) -> float:
        point = self._data_point()
        if point:
            try:
                return round(float(point.get("upperLimit")) / self._divisor(), 2)
            except (TypeError, ValueError):
                pass
        return 100.0

    @property
    def native_step(self) -> float:
        return 0.1 if self._divisor() != 1 else 1.0

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._parameter in self.coordinator.data

    async def async_set_native_value(self, value: float) -> None:
        divisor = self._divisor()
        await self.api.set_data(
            self._parameter, value, divisor=int(divisor) if divisor != 1 else None
        )
        await self.coordinator.async_request_refresh()
