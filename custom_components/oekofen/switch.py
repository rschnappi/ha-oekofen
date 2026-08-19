"""Switch platform for ÖkOfen weekly time-program day toggles."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import OekofenCoordinator
from .entity_helpers import build_device_info, parameter_available
from .pellematic_api import PellematicAPI
from .schedule_common import build_schedule_slots

_LOGGER = logging.getLogger(__name__)


def build_mode_switch_definitions(circuits: Dict[str, list]) -> Dict[str, Dict[str, Any]]:
    """Build the Party-/Urlaubsprogramm and Warmwasser one-off switch definitions."""
    defs: Dict[str, Dict[str, Any]] = {}
    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_party_aktiviert"] = {
            "parameter": f"{base}.partyprg_aktiviert",
            "name": f"{label} Partyprogramm",
            "icon": "mdi:party-popper",
        }
        defs[f"hk{idx}_urlaub_aktiviert"] = {
            "parameter": f"{base}.urlaubsprg_aktiviert",
            "name": f"{label} Urlaubsprogramm",
            "icon": "mdi:airplane",
        }
    for idx in circuits.get("ww", []):
        base = f"CAPPL:LOCAL.ww[{idx}]"
        label = f"Warmwasser {idx + 1}"
        defs[f"ww{idx}_einmal_aufbereiten"] = {
            "parameter": f"{base}.einmal_aufbereiten",
            "name": f"{label} Einmal Aufbereiten",
            "icon": "mdi:water-plus",
        }
    defs["mail_testmail"] = {
        "parameter": "CAPPL:LOCAL.L_fernwartung_sende_testmail",
        "name": "Mail Testmail senden",
        "icon": "mdi:email-fast-outline",
    }
    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the weekday-active switches plus Party-/Urlaubsprogramm switches."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    coordinator: OekofenCoordinator = entry_data["coordinator"]
    slots = build_schedule_slots(circuits)
    mode_defs = build_mode_switch_definitions(circuits)

    entities = []
    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"

    if slots:
        coordinator.add_parameters(f"{slot['base']}.block" for slot in slots)
        entities += [
            OekofenDayActiveSwitch(coordinator, api, slot, config_entry.entry_id, device_name)
            for slot in slots
        ]

    if mode_defs:
        coordinator.add_parameters(config["parameter"] for config in mode_defs.values())
        entities += [
            OekofenModeSwitch(coordinator, api, key, config, config_entry.entry_id, device_name)
            for key, config in mode_defs.items()
        ]

    if entities:
        async_add_entities(entities)


class OekofenDayActiveSwitch(CoordinatorEntity, SwitchEntity):
    """Enable/disable a weekday within an ÖkOfen weekly time program."""

    _attr_icon = "mdi:calendar-clock"
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: OekofenCoordinator,
        api: PellematicAPI,
        slot: Dict[str, Any],
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._slot = slot
        self._parameter = f"{slot['base']}.block"
        self._attr_unique_id = f"{entry_id}_{slot['key']}_active"
        self._attr_name = f"{slot['label']} Aktiv"
        self._attr_device_info = build_device_info(entry_id, device_name)

    @property
    def is_on(self) -> Optional[bool]:
        data_point = self.coordinator.data.get(self._parameter)
        if not data_point or data_point.get("value") in (None, ""):
            return None
        try:
            return int(float(data_point["value"])) != -1
        except (TypeError, ValueError):
            return None

    @property
    def available(self) -> bool:
        return parameter_available(self.coordinator, self._parameter)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate this weekday (block group 0 - matches how the device UI assigns a fresh day)."""
        await self.api.set_data(self._parameter, 0)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate this weekday."""
        await self.api.set_data(self._parameter, -1)
        await self.coordinator.async_request_refresh()


class OekofenModeSwitch(CoordinatorEntity, SwitchEntity):
    """Enable/disable ÖkOfen's Party- or Urlaubsprogramm for a heating circuit."""

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
        self._attr_device_info = build_device_info(entry_id, device_name)

    @property
    def is_on(self) -> Optional[bool]:
        point = self.coordinator.data.get(self._parameter)
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return int(float(point["value"])) == 1
        except (TypeError, ValueError):
            return None

    @property
    def available(self) -> bool:
        return parameter_available(self.coordinator, self._parameter)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.api.set_data(self._parameter, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.api.set_data(self._parameter, 0)
        await self.coordinator.async_request_refresh()
