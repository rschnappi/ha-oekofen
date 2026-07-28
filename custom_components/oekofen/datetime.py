"""Datetime platform for ÖkOfen Party-/Urlaubsprogramm absolute time fields."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .datetime_common import device_seconds_to_datetime, datetime_to_device_seconds
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


def build_datetime_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build the writable-datetime definitions (Party endzeit, Urlaub start/ende)."""
    defs: Dict[str, Dict[str, Any]] = {}

    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_party_endzeit"] = {
            "parameter": f"{base}.partyprg_endzeit",
            "name": f"{label} Party Endzeit",
            "icon": "mdi:party-popper",
        }
        defs[f"hk{idx}_urlaub_start"] = {
            "parameter": f"{base}.urlaubsprg_start",
            "name": f"{label} Urlaub Start",
            "icon": "mdi:airplane-takeoff",
        }
        defs[f"hk{idx}_urlaub_ende"] = {
            "parameter": f"{base}.urlaubsprg_ende",
            "name": f"{label} Urlaub Ende",
            "icon": "mdi:airplane-landing",
        }

    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Party-/Urlaubsprogramm datetime entities for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    definitions = build_datetime_definitions(circuits)

    if not definitions:
        return

    parameters = [config["parameter"] for config in definitions.values()]
    coordinator = OekofenDateTimeCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenDateTime(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenDateTimeCoordinator(DataUpdateCoordinator):
    """Coordinator polling the Party-/Urlaubsprogramm datetime values."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: List[str]) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Party/Urlaub Zeiten",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenDateTime(CoordinatorEntity, DateTimeEntity):
    """A writable ÖkOfen absolute datetime field (Party endzeit, Urlaub start/ende)."""

    def __init__(
        self,
        coordinator: OekofenDateTimeCoordinator,
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
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._parameter)

    @property
    def native_value(self) -> Optional[datetime]:
        point = self._data_point()
        if not point or point.get("value") in (None, ""):
            return None
        return device_seconds_to_datetime(point["value"])

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._parameter in self.coordinator.data

    async def async_set_value(self, value: datetime) -> None:
        seconds = datetime_to_device_seconds(value)
        await self.api.set_data(self._parameter, seconds)
        await self.coordinator.async_request_refresh()
