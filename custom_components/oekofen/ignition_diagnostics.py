"""Zündzeit (ignition-duration) diagnostics.

Tracks how long the boiler spends in its own "Zuendung" (ignition)
Kesselstatus phase - the window between "Start" and "Softstart" where the
Glühstab (glow plug) heats the fuel bed until flame is established. This
is the device's own, explicit ignition window (CAPPL:FA[0].L_kesselstatus),
which turned out to be far more accurate than an earlier attempt at
inferring it from the Glühstab relay's own on/off time: warm restarts
(embers still present) skip the Glühstab entirely and jump straight to
"Softstart"/"Leistungsbrand", so relay-on-time alone doesn't isolate a
real cold-start ignition the way the "Zuendung" status does.

A lengthening ignition time is a leading indicator of a worn/failing
glow plug, so this is exposed as its own sensor (with automatic
long-term statistics for trend viewing) plus a persistent notification
once a user-adjustable threshold is exceeded.

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
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity_helpers import build_device_info

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"

KESSELSTATUS_PARAMETER = "CAPPL:FA[0].L_kesselstatus"
ZUENDUNG_LABEL = "zuendung"
ZUENDZEIT_KEY = "gluehstab_zuendzeit"
WARNSCHWELLE_KEY = "gluehstab_warnschwelle"
# Based on one observed real cold-start ignition (~408s/6:48min) - tune
# this via the "Glühstab Warnschwelle" number entity once more samples
# are available.
DEFAULT_WARNSCHWELLE_SECONDS = 600.0


def _resolve_label(point: Optional[Dict[str, Any]]) -> Optional[str]:
    """Resolve a coordinator data point's raw value to its device-provided text label."""
    if not point:
        return None
    value = point.get("value")
    if value in (None, ""):
        return None
    format_texts = point.get("formatTexts") or ""
    if format_texts:
        options = format_texts.split("|")
        try:
            index = int(float(value))
        except (TypeError, ValueError):
            return None
        if 0 <= index < len(options):
            return options[index]
    return str(value)


def _is_zuendung(label: Optional[str]) -> Optional[bool]:
    if label is None:
        return None
    return label.strip().lower() == ZUENDUNG_LABEL


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


class OekofenGluehstabZuendzeit(CoordinatorEntity, RestoreSensor):
    """Duration of the boiler's last "Zuendung" (ignition) Kesselstatus phase.

    Restores its value across HA restarts (RestoreSensor) - it's only
    updated once per completed ignition, which can be hours or days apart,
    so without restoring it the sensor would drop to "unknown" on every
    restart until the next ignition happens to complete.
    """

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:heating-coil"

    def __init__(self, coordinator, entry_id: str, device_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{ZUENDZEIT_KEY}"
        self._attr_name = "Glühstab Zündzeit"
        self._attr_device_info = build_device_info(entry_id, device_name)
        self._zuendung_since: Optional[datetime] = None
        self._last_is_zuendung: Optional[bool] = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_sensor_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value

    def _handle_coordinator_update(self) -> None:
        point = self.coordinator.data.get(KESSELSTATUS_PARAMETER)
        label = _resolve_label(point)
        is_zuendung = _is_zuendung(label)

        if (
            is_zuendung is not None
            and self._last_is_zuendung is not None
            and is_zuendung != self._last_is_zuendung
        ):
            now = datetime.now(timezone.utc)
            if is_zuendung and not self._last_is_zuendung:
                # Kesselstatus wechselt in "Zuendung": neuer Zündvorgang beginnt
                self._zuendung_since = now
            elif not is_zuendung and self._last_is_zuendung and self._zuendung_since is not None:
                # Kesselstatus verlässt "Zuendung": Zündvorgang beendet, Dauer auswerten
                duration = round((now - self._zuendung_since).total_seconds())
                self._attr_native_value = duration
                self._zuendung_since = None
                self._maybe_warn(duration)

        if is_zuendung is not None:
            self._last_is_zuendung = is_zuendung

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
        self._attr_device_info = build_device_info(entry_id, device_name)
        self._attr_native_value = DEFAULT_WARNSCHWELLE_SECONDS

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
