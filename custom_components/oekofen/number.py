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
from homeassistant.const import CONF_HOST, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import OekofenCoordinator
from .ignition_diagnostics import OekofenGluehstabWarnschwelle
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

# These parameters sit behind the installer/technician PIN (main.codeebene
# >= 1) in the vendor's own web UI (config.min.js) - they're writable via
# the API, but changing them wrong can affect safety-relevant behavior
# (e.g. Kessel-Abschalttemperatur, Abgastemp-Minimum). Kept editable here
# rather than locked to read-only, but flagged clearly.
INSTALLER_WARNING = (
    "Installateur-Ebene am Original-Gerät (nur mit Techniker-Code "
    "zugänglich). Falsche Werte können die Anlage beschädigen oder "
    "Sicherheitsfunktionen beeinträchtigen - nur ändern, wenn du weißt, "
    "was du tust."
)


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
            "config": True,
        }
        defs[f"hk{idx}_heizkurve_fusspunkt"] = {
            "parameter": f"{base}.heizkurve_fusspunkt",
            "name": f"{label} Heizkurve Fußpunkt",
            "icon": "mdi:chart-line",
            "temperature": True,
            "config": True,
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
            "config": True,
        }
        defs[f"hk{idx}_raumfuehlereinfluss"] = {
            "parameter": f"{base}.raumfuehler_einfluss",
            "name": f"{label} Raumfühlereinfluss",
            "icon": "mdi:percent-outline",
            "config": True,
        }
        defs[f"hk{idx}_raumtemp_hysterese"] = {
            "parameter": f"{base}.raumtemp_plus",
            "name": f"{label} Raumtemp Hysterese",
            "icon": "mdi:thermometer",
        }
        defs[f"hk{idx}_raumtemp_urlaub"] = {
            "parameter": f"{base}.raumtemp_urlaub",
            "name": f"{label} Raumtemp Urlaub",
            "icon": "mdi:airplane",
            "temperature": True,
        }
        defs[f"hk{idx}_vorlauftemp_max"] = {
            "parameter": f"{base}.vorlauftemp_max",
            "name": f"⚠️ {label} Vorlauf Max",
            "icon": "mdi:thermometer-chevron-up",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"hk{idx}_vorlauftemp_min"] = {
            "parameter": f"{base}.vorlauftemp_min",
            "name": f"⚠️ {label} Vorlauf Min",
            "icon": "mdi:thermometer-chevron-down",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
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
        defs[f"ww{idx}_ueberhoehung"] = {
            "parameter": f"{base}.ueberhoehung",
            "name": f"⚠️ {label} Überhöhung",
            "icon": "mdi:thermometer-plus",
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"ww{idx}_nachlaufzeit"] = {
            "parameter": f"{base}.nachlaufzeit",
            "name": f"⚠️ {label} Nachlaufzeit",
            "icon": "mdi:timer-outline",
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"ww{idx}_einschalthysterese"] = {
            "parameter": f"{base}.hysterese",
            "name": f"⚠️ {label} Einschalthysterese",
            "icon": "mdi:thermometer",
            "config": True,
            "warning": INSTALLER_WARNING,
        }

    for idx in circuits.get("pellematic", []):
        base = f"CAPPL:FA[{idx}]"
        label = f"Pellematic {idx + 1}"
        defs[f"pe{idx}_kesseltemperatur_soll"] = {
            "parameter": f"{base}.pe_kesseltemperatur_soll",
            "name": f"⚠️ {label} Regeltemperatur",
            "icon": "mdi:thermometer",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"pe{idx}_abschalttemperatur"] = {
            "parameter": f"{base}.pe_abschalttemperatur",
            "name": f"⚠️ {label} Abschalttemperatur",
            "icon": "mdi:thermometer-high",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"pe{idx}_agt_min"] = {
            "parameter": f"{base}.pe_agt_min",
            "name": f"⚠️ {label} Abgastemp Minimum",
            "icon": "mdi:thermometer-low",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        # On "Smart" firmware (L_pe_schnecke_sauganlage==4), the real
        # regulation-temperature setpoint is frischwasser_soll_temp, not
        # pe_kesseltemperatur_soll (config.min.js gates the latter to
        # "!= 4" in the vendor's own einstellungen menu). Same
        # dual-firmware pattern as Leistungsstufe below: both entities
        # are created, whichever doesn't apply simply stays unavailable.
        defs[f"pe{idx}_frischwasser_soll_temp"] = {
            "parameter": f"{base}.frischwasser_soll_temp",
            "name": f"⚠️ {label} Regeltemperatur (Smart)",
            "icon": "mdi:thermometer",
            "temperature": True,
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        # "Leistungsstufe" is stored under one of two different parameter
        # names depending on whether the boiler runs classic or "Smart"
        # firmware (config.min.js switches on L_pe_schnecke_sauganlage==4).
        # Both entities are created; whichever doesn't apply to this
        # specific boiler simply stays unavailable (device never returns
        # that parameter for it), same as any other hardware-dependent field.
        defs[f"pe{idx}_leistungsstufe"] = {
            "parameter": f"{base}.pe_kesselleistung",
            "name": f"⚠️ {label} Leistungsstufe",
            "icon": "mdi:fire",
            "config": True,
            "warning": INSTALLER_WARNING,
        }
        defs[f"pe{idx}_leistungsstufe_smart"] = {
            "parameter": f"{base}.pe_kesselleistung_smart",
            "name": f"⚠️ {label} Leistungsstufe (Smart)",
            "icon": "mdi:fire",
            "config": True,
            "warning": INSTALLER_WARNING,
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
    coordinator = entry_data["coordinator"]
    definitions = build_number_definitions(circuits)
    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"

    entities: List[Any] = [OekofenGluehstabWarnschwelle(config_entry.entry_id, device_name)]

    if definitions:
        parameters = [config["parameter"] for config in definitions.values()]
        coordinator.add_parameters(parameters)
        entities += [
            OekofenNumber(coordinator, api, key, config, config_entry.entry_id, device_name)
            for key, config in definitions.items()
        ]

    async_add_entities(entities)


class OekofenNumber(CoordinatorEntity, NumberEntity):
    """A writable ÖkOfen setpoint, with limits/divisor read from the device itself."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OekofenCoordinator,
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
        # Always assign _attr_entity_category (None when not a config field):
        # like _attr_preset_modes on ClimateEntity, this has no class-level
        # default on newer Home Assistant versions, so leaving it unset
        # raises AttributeError instead of returning None.
        self._attr_entity_category = EntityCategory.CONFIG if config.get("config") else None
        self._warning: Optional[str] = config.get("warning")
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        if self._warning:
            return {"warnhinweis": self._warning}
        return None

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
