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
from homeassistant.util import dt as dt_util

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

    *** EXPERIMENTAL - the DST-dependent compensation below is a working
    hypothesis, not yet confirmed with a real winter-time data point. ***

    Shared between OekofenDateTime.async_set_value (device_clock field) and
    button.py's one-press "sync now" button. Applies a -2h/-4h compensation
    depending on whether Europe/Vienna is currently on DST (see
    _device_clock_compensation_hours below for why): the device applies its
    own extra shift once L_fernwartung_setze_uhrzeit actually commits the
    staged value into the device's *running* clock - unlike every other
    datetime field here (Party endzeit, Urlaub start/ende), which just
    store a future timestamp compared against that running clock later and
    don't exhibit this. This correction belongs here, not in
    datetime_common.py's shared conversion, which the read side
    (device_seconds_to_datetime, for DEVICE_CLOCK_READ_PARAMETER) and the
    other fields are already verified correct against.
    History: confirmed live against a real device during CEST
    (2026-09-05/06), in two rounds - an initial -2h compensation (based on
    a single same-evening data point) still left the device's native web
    UI showing 2h ahead of actual time the next morning, on a freshly
    reloaded page (ruling out a stale browser tab), i.e. the device's own
    shift during DST is +4h total, not +2h. Both data points so far were
    taken while DST was active - the device's owner suspects the
    device-side shift is actually a fixed, DST-naive +2h that only reads
    as +4h while DST is active (the device presumably has no timezone
    concept of its own and just always adds a flat 2 wall-clock hours,
    which happens to line up with CEST-vs-UTC but not with the actual
    CEST-vs-CET difference) and would drop back to +2h once Europe/Vienna
    returns to CET (winter time). NOT YET CONFIRMED - no real winter-time
    data point exists yet; re-verify live around/after the next DST switch
    (late October) before trusting this across a season boundary.
    CAUTION: setting this field wrong once briefly locked the whole device
    out (HTTP 403 on every request) - the device's session cookie appears
    to be time-bound, so a clock that jumps by hours can invalidate the
    very session used to fix it. Recovery: homeassistant.reload_config_entry
    on this entry (forces a fresh login/cookie) - do NOT restart HA for
    this alone, and don't retry writes to this field in a loop hoping a
    different value fixes it. Given the above, treat this field
    conservatively (verify the result after every use) rather than
    trusting it unattended.
    """
    compensation_hours = _device_clock_compensation_hours(value)
    seconds = datetime_to_device_seconds(value) - compensation_hours * 3600
    await api.set_data_multi({DEVICE_CLOCK_PARAMETER: seconds, DEVICE_CLOCK_COMMIT_PARAMETER: 1})


def _device_clock_compensation_hours(value: datetime) -> int:
    """4h while Europe/Vienna is on DST (CEST), 2h otherwise (CET) - see
    async_commit_device_clock's docstring for the (unconfirmed) reasoning:
    a hypothesized fixed +2h device-side shift that only reads as +4h
    because both data points calibrating this were taken during DST."""
    return 4 if dt_util.as_local(value).dst() else 2


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
