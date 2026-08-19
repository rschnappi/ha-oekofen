"""Select platform for ÖkOfen operating modes and active-schedule choice.

Option labels are read live from the device's own "formatTexts" field
whenever the device provides them (that's how the vendor's own web
interface builds its dropdowns too). A static fallback list is used
only for the handful of parameters that don't carry formatTexts on
older firmware, so the entity still works if the device omits them.
"""
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .betriebsart import (
    ANLAGE_MODE_PARAMETER,
    AUS_MODE_HINWEIS,
    active_betriebsart_slot,
    betriebsart_parameter,
    betriebsart_slot_parameters,
)
from .coordinator import OekofenCoordinator
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

# See number.py's INSTALLER_WARNING for context: these two parameters sit
# behind the installer/technician PIN in the vendor's own web UI.
INSTALLER_WARNING = (
    "Installateur-Ebene am Original-Gerät (nur mit Techniker-Code "
    "zugänglich). Falsche Werte können die Anlage beschädigen oder "
    "Sicherheitsfunktionen beeinträchtigen - nur ändern, wenn du weißt, "
    "was du tust."
)


def build_select_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build the select definitions for the circuits/units present on this device."""
    defs: Dict[str, Dict[str, Any]] = {
        "system_mode": {
            "parameter": "CAPPL:LOCAL.anlage_betriebsart",
            "name": "Anlage Betriebsart",
            "icon": "mdi:tune",
            "fallback_options": ["Aus", "Auto", "Warmwasser"],
        }
    }

    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_mode"] = {
            "betriebsart_base": base,
            "name": f"{label} Betriebsart",
            "icon": "mdi:radiator",
            "fallback_options": ["Aus", "Auto", "Heizen", "Absenken"],
        }
        defs[f"hk{idx}_zeitprogramm"] = {
            "parameter": f"{base}.aktives_zeitprogramm",
            "name": f"{label} Aktives Zeitprogramm",
            "icon": "mdi:calendar-clock",
            "fallback_options": ["Zeit 1", "Zeit 2"],
        }

    for idx in circuits.get("ww", []):
        base = f"CAPPL:LOCAL.ww[{idx}]"
        label = f"Warmwasser {idx + 1}"
        defs[f"ww{idx}_mode"] = {
            "betriebsart_base": base,
            "name": f"{label} Betriebsart",
            "icon": "mdi:water-boiler",
            "fallback_options": ["Aus", "Auto", "Ein"],
        }
        defs[f"ww{idx}_zeitprogramm"] = {
            "parameter": f"{base}.aktives_zeitprogramm",
            "name": f"{label} Aktives Zeitprogramm",
            "icon": "mdi:calendar-clock",
            "fallback_options": ["Zeit 1", "Zeit 2"],
        }
        defs[f"ww{idx}_vorrang"] = {
            "parameter": f"{base}.prioritaet",
            "name": f"⚠️ {label} Vorrang",
            "icon": "mdi:priority-high",
            "fallback_options": ["Ein", "Aus"],
            "warning": INSTALLER_WARNING,
        }
        defs[f"ww{idx}_legionellenschutz"] = {
            "parameter": f"{base}.legionellen_wochentag",
            "name": f"⚠️ {label} Legionellenschutz",
            "icon": "mdi:shield-check",
            "fallback_options": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So", "Aus"],
            "warning": INSTALLER_WARNING,
        }

    for idx in circuits.get("zirkp", []):
        base = f"CAPPL:LOCAL.zirkp[{idx}]"
        label = f"Zirkulationspumpe {idx + 1}"
        defs[f"zirkp{idx}_mode"] = {
            "parameter": f"{base}.betriebsart",
            "name": f"{label} Betriebsart",
            "icon": "mdi:pump",
            "fallback_options": ["Aus", "Auto", "Ein"],
        }
        defs[f"zirkp{idx}_zeitprogramm"] = {
            "parameter": f"{base}.aktives_zeitprogramm",
            "name": f"{label} Aktives Zeitprogramm",
            "icon": "mdi:calendar-clock",
            "fallback_options": ["Zeit 1", "Zeit 2"],
        }

    for idx in circuits.get("pellematic", []):
        base = f"CAPPL:FA[{idx}]"
        label = f"Pellematic {idx + 1}"
        defs[f"pe{idx}_mode"] = {
            "parameter": f"{base}.betriebsart_fa",
            "name": f"{label} Betriebsart",
            "icon": "mdi:fire",
            "fallback_options": ["Aus", "Auto", "Ein"],
        }

    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    coordinator = entry_data["coordinator"]
    definitions = build_select_definitions(circuits)

    if not definitions:
        return

    parameters: List[str] = []
    for config in definitions.values():
        if config.get("betriebsart_base"):
            parameters += betriebsart_slot_parameters(config["betriebsart_base"])
        else:
            parameters.append(config["parameter"])
    if ANLAGE_MODE_PARAMETER not in parameters:
        parameters.append(ANLAGE_MODE_PARAMETER)
    coordinator.add_parameters(parameters)

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenModeSelect(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenModeSelect(CoordinatorEntity, SelectEntity):
    """A writable ÖkOfen enum parameter, exposed as an HA select dropdown."""

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
        self._betriebsart_base = config.get("betriebsart_base")
        self._parameter = config.get("parameter")
        self._fallback_options = config.get("fallback_options", [])
        self._warning: Optional[str] = config.get("warning")
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = config.get("icon")
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        attrs: Dict[str, Any] = {}
        if self._warning:
            attrs["warnhinweis"] = self._warning
        if self._betriebsart_base and active_betriebsart_slot(self.coordinator.data) == 0:
            attrs["hinweis"] = AUS_MODE_HINWEIS
        return attrs or None

    def _current_parameter(self) -> str:
        if self._betriebsart_base:
            return betriebsart_parameter(self._betriebsart_base, self.coordinator.data)
        return self._parameter

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._current_parameter())

    @property
    def options(self) -> List[str]:
        point = self._data_point()
        format_texts = (point.get("formatTexts") if point else "") or ""
        format_texts = format_texts.strip()
        if format_texts:
            return [text.strip() for text in format_texts.split("|")]
        return self._fallback_options

    @property
    def current_option(self) -> Optional[str]:
        point = self._data_point()
        if not point or point.get("value") in (None, ""):
            return None
        try:
            index = int(float(point["value"]))
        except (TypeError, ValueError):
            return None
        options = self.options
        if 0 <= index < len(options):
            return options[index]
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._current_parameter() in self.coordinator.data

    async def async_select_option(self, option: str) -> None:
        options = self.options
        if option not in options:
            raise ValueError(f"Unknown option '{option}' for {self._current_parameter()}")
        parameter = self._current_parameter()
        await self.api.set_data(parameter, options.index(option))
        await self.coordinator.async_request_refresh()
