"""Datetime platform for ÖkOfen Party-/Urlaubsprogramm absolute time fields."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import OekofenCoordinator
from .datetime_common import device_seconds_to_datetime, datetime_to_device_seconds
from .entity_helpers import build_device_info, parameter_available
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

# The device's own clock. Unlike everything else, the *current* value and
# the *write target* are different parameters: the running clock is
# L_fernwartung_datum_zeit_sek, while a new value is staged in
# L_fernwartung_uhrzeit_neu and only takes effect once
# L_fernwartung_setze_uhrzeit=1 is sent in the same request (the device's
# own web UI always sends these two together, see config.min.js
# "zusatzVariable"). Exposed as module-level constants (not just inline in
# build_datetime_definitions below) so button.py's one-press sync button
# can target the same parameters without redefining the strings.
DEVICE_CLOCK_PARAMETER = "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu"
DEVICE_CLOCK_READ_PARAMETER = "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek"
DEVICE_CLOCK_COMMIT_PARAMETER = "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit"


async def async_commit_device_clock(api: PellematicAPI, value: datetime) -> None:
    """Stage `value` into the device's own running clock and commit it.

    Shared between OekofenDateTime.async_set_value (device_clock field) and
    button.py's one-press "sync now" button. Applies a -2h compensation:
    the device applies its own extra +2h shift once
    L_fernwartung_setze_uhrzeit actually commits the staged value into the
    device's *running* clock - unlike every other datetime field here
    (Party endzeit, Urlaub start/ende), which just store a future timestamp
    compared against that running clock later and don't exhibit this.
    Confirmed live against a real device (2026-09-05): setting this entity
    to a value X made the device's own clock show X+2h, both via this
    integration and via the device's native web UI's own date/time field -
    so this correction belongs here, not in datetime_common.py's shared
    conversion, which the read side (device_seconds_to_datetime, for
    DEVICE_CLOCK_READ_PARAMETER) and the other fields are already verified
    correct against.
    CAUTION: setting this field wrong once briefly locked the whole device
    out (HTTP 403 on every request) - the device's session cookie appears
    to be time-bound, so a clock that jumps by hours can invalidate the
    very session used to fix it. Recovery: homeassistant.reload_config_entry
    on this entry (forces a fresh login/cookie) - do NOT restart HA for
    this alone, and don't retry writes to this field in a loop hoping a
    different value fixes it.
    """
    seconds = datetime_to_device_seconds(value) - 2 * 3600
    await api.set_data_multi({DEVICE_CLOCK_PARAMETER: seconds, DEVICE_CLOCK_COMMIT_PARAMETER: 1})


def build_datetime_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build the writable-datetime definitions (Party endzeit, Urlaub start/ende)."""
    defs: Dict[str, Dict[str, Any]] = {
        "device_clock": {
            "parameter": DEVICE_CLOCK_PARAMETER,
            "read_parameter": DEVICE_CLOCK_READ_PARAMETER,
            "commit_parameter": DEVICE_CLOCK_COMMIT_PARAMETER,
            "name": "Geräteuhrzeit",
            "icon": "mdi:clock-edit-outline",
        },
    }

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
    coordinator: OekofenCoordinator = entry_data["coordinator"]
    definitions = build_datetime_definitions(circuits)

    if not definitions:
        return

    parameters = sorted({
        param
        for config in definitions.values()
        for param in (config["parameter"], config.get("read_parameter", config["parameter"]))
    })
    coordinator.add_parameters(parameters)

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenDateTime(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenDateTime(CoordinatorEntity, DateTimeEntity):
    """A writable ÖkOfen absolute datetime field (Party endzeit, Urlaub start/ende)."""

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
        self._read_parameter = config.get("read_parameter", self._parameter)
        self._commit_parameter = config.get("commit_parameter")
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = config.get("icon")
        self._attr_device_info = build_device_info(entry_id, device_name)

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._read_parameter)

    @property
    def native_value(self) -> Optional[datetime]:
        point = self._data_point()
        if not point or point.get("value") in (None, ""):
            return None
        return device_seconds_to_datetime(point["value"])

    @property
    def available(self) -> bool:
        return parameter_available(self.coordinator, self._read_parameter)

    async def async_set_value(self, value: datetime) -> None:
        if self._commit_parameter:
            await async_commit_device_clock(self.api, value)
        else:
            seconds = datetime_to_device_seconds(value)
            await self.api.set_data(self._parameter, seconds)
        await self.coordinator.async_request_refresh()
