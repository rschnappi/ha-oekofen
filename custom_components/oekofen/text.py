"""Text platform for the ÖkOfen Fernwartung/Mail (SMTP) settings.

Parameter names come from the vendor's own config.min.js, menu path
Allgemeines -> Internet ("Internet"/"Mail-Einstellungen"). These are
global device settings (not per heating/hot-water circuit), so unlike
number.py/select.py/switch.py there is no per-circuit definitions loop.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EntityCategory
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

MAIL_EMPFAENGER_COUNT = 5


def build_text_definitions() -> Dict[str, Dict[str, Any]]:
    """Build the Fernwartung/Mail text-field definitions."""
    defs: Dict[str, Dict[str, Any]] = {
        "mail_anlagenbezeichnung": {
            "parameter": "CAPPL:LOCAL.fernwartung_anlagenbezeichung",
            "name": "Mail Anlagenbezeichnung",
            "icon": "mdi:card-text-outline",
            "mode": TextMode.TEXT,
        },
        "mail_postausgangsserver": {
            "parameter": "CAPPL:LOCAL.fernwartung_mail_postausgangsserver",
            "name": "Mail SMTP-Server",
            "icon": "mdi:server-network",
            "mode": TextMode.TEXT,
        },
        "mail_benutzer": {
            "parameter": "CAPPL:LOCAL.fernwartung_mail_benutzer",
            "name": "Mail SMTP-Benutzer",
            "icon": "mdi:account-outline",
            "mode": TextMode.TEXT,
        },
        "mail_passwort": {
            "parameter": "CAPPL:LOCAL.fernwartung_mail_passwort",
            "name": "Mail SMTP-Passwort",
            "icon": "mdi:key-outline",
            "mode": TextMode.PASSWORD,
        },
    }
    for idx in range(MAIL_EMPFAENGER_COUNT):
        defs[f"mail_empfaenger_{idx}"] = {
            "parameter": f"CAPPL:LOCAL.fernwartung_mail_empfaenger[{idx}]",
            "name": f"Mail Empfänger {idx + 1}",
            "icon": "mdi:email-outline",
            "mode": TextMode.TEXT,
        }
    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fernwartung/Mail text entities for a config entry."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    definitions = build_text_definitions()

    parameters = [config["parameter"] for config in definitions.values()]
    coordinator = OekofenTextCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenText(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenTextCoordinator(DataUpdateCoordinator):
    """Coordinator polling the Fernwartung/Mail text values."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: List[str]) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Fernwartung",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenText(CoordinatorEntity, TextEntity):
    """A writable ÖkOfen Fernwartung/Mail text field."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: OekofenTextCoordinator,
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
        self._attr_mode = config.get("mode", TextMode.TEXT)
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    def _data_point(self) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(self._parameter)

    @property
    def native_value(self) -> Optional[str]:
        point = self._data_point()
        if not point or point.get("value") is None:
            return None
        return str(point["value"])

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._parameter in self.coordinator.data

    async def async_set_value(self, value: str) -> None:
        await self.api.set_data(self._parameter, value)
        await self.coordinator.async_request_refresh()
