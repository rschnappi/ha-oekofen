"""Time platform for ÖkOfen weekly time-program start/end times."""
import logging
from datetime import time as dt_time
from typing import Any, Dict, Optional

from homeassistant.components.time import TimeEntity
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
from .schedule_common import (
    BLOCKS_PER_DAY,
    SCAN_INTERVAL,
    build_schedule_slots,
    seconds_to_time,
    time_to_seconds,
)

_LOGGER = logging.getLogger(__name__)

BLOCK_LABELS = {0: "Block 1", 1: "Block 2", 2: "Block 3"}
EDGE_LABELS = {0: "Von", 1: "Bis"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the schedule start/end time entities for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    slots = build_schedule_slots(circuits)

    if not slots:
        return

    parameters = []
    for slot in slots:
        for block in range(BLOCKS_PER_DAY):
            parameters.append(f"{slot['base']}.zeitreihe[{block},0]")
            parameters.append(f"{slot['base']}.zeitreihe[{block},1]")

    coordinator = OekofenScheduleTimeCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = []
    for slot in slots:
        for block in range(BLOCKS_PER_DAY):
            for edge in (0, 1):
                entities.append(
                    OekofenScheduleTimeEntity(
                        coordinator, api, slot, block, edge, config_entry.entry_id, device_name
                    )
                )
    async_add_entities(entities)


class OekofenScheduleTimeCoordinator(DataUpdateCoordinator):
    """Coordinator polling the start/end time values."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: list) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Zeitprogramm (Uhrzeiten)",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenScheduleTimeEntity(CoordinatorEntity, TimeEntity):
    """Start or end time of one schedule block within an ÖkOfen weekday program."""

    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: OekofenScheduleTimeCoordinator,
        api: PellematicAPI,
        slot: Dict[str, Any],
        block: int,
        edge: int,
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._slot = slot
        self._block = block
        self._edge = edge  # 0 = start ("Von"), 1 = end ("Bis")
        self._parameter = f"{slot['base']}.zeitreihe[{block},{edge}]"
        self._attr_unique_id = (
            f"{entry_id}_{slot['key']}_block{block}_{EDGE_LABELS[edge].lower()}"
        )
        self._attr_name = f"{slot['label']} {BLOCK_LABELS[block]} {EDGE_LABELS[edge]}"
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    @property
    def native_value(self) -> Optional[dt_time]:
        data_point = self.coordinator.data.get(self._parameter)
        if not data_point:
            return None
        return seconds_to_time(data_point.get("value"))

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._parameter in self.coordinator.data

    async def async_set_value(self, value: dt_time) -> None:
        seconds = time_to_seconds(value)
        await self.api.set_data(self._parameter, seconds)
        await self.coordinator.async_request_refresh()
