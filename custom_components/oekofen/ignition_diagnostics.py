"""Glühstab (glow plug) ignition-duration diagnostics.

Tracks how long the igniter (CAPPL:FA[0].ausgang_motor[1]) stays energized
during each ignition cycle. A lengthening ignition time is a leading
indicator of a worn/failing glow plug, so this is exposed as its own
sensor (with automatic long-term statistics for trend viewing) plus a
persistent notification once a user-adjustable threshold is exceeded.

The threshold is a plain Home Assistant-side setting (not backed by any
device parameter), so it's looked up by unique_id via the entity
registry rather than by guessing its entity_id - Home Assistant's
slugify only strips umlauts rather than transliterating them (ä -> a,
not ae), which has already caused mismatched dashboard entity_ids once
this session.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"

GLUEHSTAB_PARAMETER = "CAPPL:FA[0].ausgang_motor[1]"
ZUENDZEIT_KEY = "gluehstab_zuendzeit"
WARNSCHWELLE_KEY = "gluehstab_warnschwelle"
DEFAULT_WARNSCHWELLE_SECONDS = 240.0


def _is_off(value: Optional[str]) -> Optional[bool]:
    """Whether a Glühstab formatText value means "off" (device sends e.g. " Aus")."""
    if value in (None, ""):
        return None
    return str(value).strip().lower() == "aus"


def get_warnschwelle(hass: HomeAssistant, entry_id: str, default: float = DEFAULT_WARNSCHWELLE_SECONDS) -> float:
    """Look up the current Glühstab-Warnschwelle value via the entity registry."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("number", DOMAIN, f"{entry_id}_{WARNSCHWELLE_KEY}")
    if entity_id:
        state = hass.states.get(entity_id)
        if state and state.state not in (None, "unknown", "unavailable"):
            try:
                return float(state.state)
            except ValueError:
                pass
    return default


class OekofenGluehstabZuendzeit(CoordinatorEntity, SensorEntity):
    """Duration the Glühstab stayed energized during the last ignition cycle."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:heating-coil"

    def __init__(self, coordinator, entry_id: str, device_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{ZUENDZEIT_KEY}"
        self._attr_name = "Glühstab Zündzeit"
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }
        self._on_since: Optional[datetime] = None
        self._last_state_off: Optional[bool] = None

    def _handle_coordinator_update(self) -> None:
        point = self.coordinator.data.get(GLUEHSTAB_PARAMETER)
        is_off = _is_off(point.get("value")) if point else None

        if is_off is not None and self._last_state_off is not None and is_off != self._last_state_off:
            now = datetime.now(timezone.utc)
            if self._last_state_off and not is_off:
                # Aus -> an: neue Zündung beginnt
                self._on_since = now
            elif not self._last_state_off and is_off and self._on_since is not None:
                # an -> Aus: Zündung beendet, Dauer auswerten
                duration = round((now - self._on_since).total_seconds())
                self._attr_native_value = duration
                self._on_since = None
                self._maybe_warn(duration)

        if is_off is not None:
            self._last_state_off = is_off

        super()._handle_coordinator_update()

    def _maybe_warn(self, duration: float) -> None:
        threshold = get_warnschwelle(self.hass, self._entry_id)
        if duration <= threshold:
            return
        async_create_notification(
            self.hass,
            (
                f"Die letzte Zündung hat {duration:.0f} Sekunden gedauert "
                f"(Schwelle: {threshold:.0f} s). Das kann auf einen "
                f"schwächelnden Glühstab hindeuten."
            ),
            title="ÖkOfen: Zündzeit auffällig",
            notification_id=f"oekofen_gluehstab_warnung_{self._entry_id}",
        )


class OekofenGluehstabWarnschwelle(RestoreNumber):
    """User-adjustable ignition-duration warning threshold.

    Purely local to Home Assistant - not backed by any device parameter.
    """

    _attr_native_min_value = 30
    _attr_native_max_value = 900
    _attr_native_step = 10
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:alert-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry_id: str, device_name: str) -> None:
        self._attr_unique_id = f"{entry_id}_{WARNSCHWELLE_KEY}"
        self._attr_name = "Glühstab Warnschwelle"
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }
        self._attr_native_value = DEFAULT_WARNSCHWELLE_SECONDS

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
