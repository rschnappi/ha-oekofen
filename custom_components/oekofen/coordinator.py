"""Single shared DataUpdateCoordinator for a whole ÖkOfen config entry.

Every platform (select/number/climate/sensor/switch/time/datetime/text)
used to run its own DataUpdateCoordinator, each polling the device
independently and often overlapping (e.g. CAPPL:LOCAL.anlage_betriebsart
was fetched separately by both select.py and climate.py) - up to ~11
separate HTTP requests per polling cycle against the device's fairly
weak embedded web server. Platforms now register the parameters they
need into this one shared coordinator instead (via add_parameters), so
the whole config entry does a single combined request per cycle.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, Iterable, Set

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

# Faster than any individual platform coordinator used to poll at before
# (climate.py/sensor.py were the fastest, at 30s) - affordable now that
# consolidation means one combined request per cycle instead of up to ~11
# separate ones, so every parameter refreshes more often than any platform
# got individually before.
SCAN_INTERVAL = timedelta(seconds=15)


class OekofenCoordinator(DataUpdateCoordinator):
    """Polls every parameter registered by any platform in one request.

    Platforms call add_parameters() during their async_setup_entry, before
    __init__.py triggers the first refresh once all platforms have been
    forwarded - see async_setup_entry in __init__.py.
    """

    def __init__(self, hass: HomeAssistant, api: PellematicAPI) -> None:
        self.api = api
        self.parameters: Set[str] = set()
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Pellematic",
            update_interval=SCAN_INTERVAL,
        )

    def add_parameters(self, parameters: Iterable[str]) -> None:
        """Register parameters a platform needs polled."""
        self.parameters.update(parameters)

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(list(self.parameters))
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err
