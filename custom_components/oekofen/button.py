"""Button platform - one-click device clock sync (see datetime.py's device_clock)."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import OekofenCoordinator
from .datetime import DEVICE_CLOCK_READ_PARAMETER, async_commit_device_clock
from .entity_helpers import build_device_info, parameter_available
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device-clock sync button for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    coordinator: OekofenCoordinator = entry_data["coordinator"]

    # datetime.py's own async_setup_entry already registers
    # DEVICE_CLOCK_READ_PARAMETER for the device_clock datetime entity -
    # add_parameters just merges into one shared set regardless of platform
    # setup order (see coordinator.py), so registering it again here for
    # this button's own availability check is harmless.
    coordinator.add_parameters([DEVICE_CLOCK_READ_PARAMETER])

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    async_add_entities([
        OekofenSyncClockButton(coordinator, api, config_entry.entry_id, device_name)
    ])


class OekofenSyncClockButton(CoordinatorEntity, ButtonEntity):
    """Sets the device's own clock to Home Assistant's current time.

    A one-press shortcut for the device_clock datetime entity (datetime.py)
    - reuses async_commit_device_clock there, including its -2h
    compensation for the device's own commit-time quirk, instead of
    requiring the user to manually pick "now" as a datetime value.
    """

    _attr_icon = "mdi:clock-check-outline"

    def __init__(
        self,
        coordinator: OekofenCoordinator,
        api: PellematicAPI,
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._attr_unique_id = f"{entry_id}_device_clock_sync"
        self._attr_name = "Geräteuhrzeit synchronisieren"
        self._attr_device_info = build_device_info(entry_id, device_name)

    @property
    def available(self) -> bool:
        return parameter_available(self.coordinator, DEVICE_CLOCK_READ_PARAMETER)

    async def async_press(self) -> None:
        await async_commit_device_clock(self.api, dt_util.utcnow())
        await self.coordinator.async_request_refresh()
