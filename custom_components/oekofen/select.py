"""Select platform for ÖkOfen operating modes and active-schedule choice.

Option labels are read live from the device's own "formatTexts" field
whenever the device provides them (that's how the vendor's own web
interface builds its dropdowns too). A static fallback list is used
only for the handful of parameters that don't carry formatTexts on
older firmware, so the entity still works if the device omits them.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


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
            "parameter": f"{base}.betriebsart[0]",
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
            "parameter": f"{base}.betriebsart[0]",
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
            "name": f"{label} Vorrang",
            "icon": "mdi:priority-high",
            "fallback_options": ["Ein", "Aus"],
        }
        defs[f"ww{idx}_legionellenschutz"] = {
            "parameter": f"{base}.legionellen_wochentag",
            "name": f"{label} Legionellenschutz",
            "icon": "mdi:shield-check",
            "fallback_options": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So", "Aus"],
        }

    for idx in circuits.get("zirkp", []):
        base = f"CAPPL:LOCAL.zirkp[{idx}]"
        label = f"Zirkulationspumpe {idx + 1}"
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
    definitions = build_select_definitions(circuits)

    if not definitions:
        return

    parameters = [config["parameter"] for config in definitions.values()]
    coordinator = OekofenSelectCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenModeSelect(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenSelectCoordinator(DataUpdateCoordinator):
    """Coordinator polling the mode/schedule-selection values."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: List[str]) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Betriebsarten",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenModeSelect(CoordinatorEntity, SelectEntity):
    """A writable ÖkOfen enum parameter, exposed as an HA select dropdown."""

    def __init__(
        self,
        coordinator: OekofenSelectCoordinator,
        api: PellematicAPI,
        key: str,
        config: Dict[str, Any],
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._parameter = config["parameter"]
        self._fallback_options = config.get("fallback_options", [])
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = config.get("icon")
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._parameter)

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
        return self.coordinator.last_update_success and self._parameter in self.coordinator.data

    async def async_select_option(self, option: str) -> None:
        options = self.options
        if option not in options:
            raise ValueError(f"Unknown option '{option}' for {self._parameter}")
        await self.api.set_data(self._parameter, options.index(option))
        await self.coordinator.async_request_refresh()
