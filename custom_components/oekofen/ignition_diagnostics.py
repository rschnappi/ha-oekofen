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
from dataclasses import dataclass
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
from homeassistant.helpers.restore_state import ExtraStoredData
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .entity_helpers import build_device_info

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"

KESSELSTATUS_PARAMETER = "CAPPL:FA[0].L_kesselstatus"
ZUENDUNG_LABEL = "zuendung"
ZUENDZEIT_KEY = "gluehstab_zuendzeit"
WARNSCHWELLE_KEY = "gluehstab_warnschwelle"
# Based on one observed real cold-start ignition (~408s/6.8min) - tune
# this via the "Glühstab Warnschwelle" number entity once more samples
# are available. Both this and OekofenGluehstabZuendzeit's own value are
# in minutes (not seconds) - realistic ignitions run a few minutes, and
# seconds-level precision doesn't matter for a "is this trending up"
# indicator.
DEFAULT_WARNSCHWELLE_MINUTES = 10.0
# A previously-restored value above this is unambiguously a leftover from
# before entities here were in seconds, not a plausible minutes value -
# see the migration handling in async_added_to_hass on both entities below.
_LEGACY_SECONDS_VALUE_THRESHOLD = 60.0


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


def get_warnschwelle(hass: HomeAssistant, entry_id: str, default: float = DEFAULT_WARNSCHWELLE_MINUTES) -> float:
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


@dataclass
class _ZuendzeitExtraStoredData(ExtraStoredData):
    """Adds the in-progress-ignition tracking state to what RestoreSensor
    normally persists (just native_value) - see the class docstring below
    on why that in-progress state needs restoring too."""

    native_value: Optional[int]
    zuendung_since: Optional[datetime]
    last_is_zuendung: Optional[bool]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "native_value": self.native_value,
            "zuendung_since": self.zuendung_since.isoformat() if self.zuendung_since else None,
            "last_is_zuendung": self.last_is_zuendung,
        }

    @classmethod
    def from_dict(cls, restored: Dict[str, Any]) -> "_ZuendzeitExtraStoredData":
        zuendung_since = restored.get("zuendung_since")
        return cls(
            native_value=restored.get("native_value"),
            zuendung_since=dt_util.parse_datetime(zuendung_since) if zuendung_since else None,
            last_is_zuendung=restored.get("last_is_zuendung"),
        )


class OekofenGluehstabZuendzeit(CoordinatorEntity, RestoreSensor):
    """Duration of the boiler's last "Zuendung" (ignition) Kesselstatus phase.

    Restores its value across HA restarts (RestoreSensor) - it's only
    updated once per completed ignition, which can be hours or days apart,
    so without restoring it the sensor would drop to "unknown" on every
    restart until the next ignition happens to complete.

    Also restores _zuendung_since/_last_is_zuendung (via a custom
    extra_restore_state_data, not RestoreSensor's default which only covers
    native_value): without that, a restart landing while the boiler is
    actively mid-ignition loses track of when it started, and that cycle's
    duration is silently never recorded once it completes - not a crash,
    just a dropped sample, but exactly the kind of restart-shaped gap this
    integration has already been bitten by elsewhere.
    """

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:heating-coil"

    def __init__(self, coordinator, entry_id: str, device_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{ZUENDZEIT_KEY}"
        self._attr_name = "Glühstab Zündzeit"
        self._attr_device_info = build_device_info(entry_id, device_name)
        self._zuendung_since: Optional[datetime] = None
        self._last_is_zuendung: Optional[bool] = None

    @property
    def extra_restore_state_data(self) -> _ZuendzeitExtraStoredData:
        return _ZuendzeitExtraStoredData(
            native_value=self.native_value,
            zuendung_since=self._zuendung_since,
            last_is_zuendung=self._last_is_zuendung,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._async_migrate_unit_override()
        last_extra_data = await self.async_get_last_extra_data()
        if last_extra_data is None:
            return
        restored = _ZuendzeitExtraStoredData.from_dict(last_extra_data.as_dict())
        if restored.native_value is not None:
            value = restored.native_value
            if value > _LEGACY_SECONDS_VALUE_THRESHOLD:
                # Restored from before this sensor switched from seconds to
                # minutes - convert rather than displaying e.g. "408 min".
                value = round(value / 60, 1)
            self._attr_native_value = value
        self._zuendung_since = restored.zuendung_since
        self._last_is_zuendung = restored.last_is_zuendung

    def _async_migrate_unit_override(self) -> None:
        """Undo HA's own automatic "keep the old unit" protection.

        SensorEntity.add_to_platform_start (see homeassistant/components/
        sensor/__init__.py) runs on every add-to-hass, before this method:
        if a duration-class sensor's computed unit differs from what's
        already on file in the entity registry, and no user override
        exists yet, it silently writes a `sensor.private.
        suggested_unit_of_measurement` registry option pinned to the *old*
        unit - specifically so existing statistics/dashboards don't break
        when an integration changes its native unit. That's exactly what
        happened here: switching this sensor from seconds to minutes just
        made every future minute value get converted back to seconds for
        display (a native 8.2 stayed correct internally, but showed as
        "492 s"). Since minutes is what we actually want going forward,
        clear that pin once it's stale.
        """
        if self.registry_entry is None:
            return
        private_options = self.registry_entry.options.get("sensor.private") or {}
        pinned_unit = private_options.get("suggested_unit_of_measurement")
        if not pinned_unit or pinned_unit == self.native_unit_of_measurement:
            return
        registry = er.async_get(self.hass)
        self.registry_entry = registry.async_update_entity_options(
            self.entity_id, "sensor.private", None
        )
        self._async_read_entity_options()

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
                duration_minutes = round((now - self._zuendung_since).total_seconds() / 60, 1)
                self._attr_native_value = duration_minutes
                self._zuendung_since = None
                self._maybe_warn(duration_minutes)

        if is_zuendung is not None:
            self._last_is_zuendung = is_zuendung

        super()._handle_coordinator_update()

    def _maybe_warn(self, duration_minutes: float) -> None:
        threshold = get_warnschwelle(self.hass, self._entry_id)
        if duration_minutes <= threshold:
            return
        async_create_notification(
            self.hass,
            (
                f"Die letzte Zündung hat {duration_minutes:.1f} Minuten gedauert "
                f"(Schwelle: {threshold:.1f} min). Das kann auf einen "
                f"schwächelnden Glühstab hindeuten."
            ),
            title="ÖkOfen: Zündzeit auffällig",
            notification_id=f"oekofen_gluehstab_warnung_{self._entry_id}",
        )


class OekofenGluehstabWarnschwelle(RestoreNumber):
    """User-adjustable ignition-duration warning threshold.

    Purely local to Home Assistant - not backed by any device parameter.
    """

    _attr_native_min_value = 1
    _attr_native_max_value = 15
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:alert-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, entry_id: str, device_name: str) -> None:
        self._attr_unique_id = f"{entry_id}_{WARNSCHWELLE_KEY}"
        self._attr_name = "Glühstab Warnschwelle"
        self._attr_device_info = build_device_info(entry_id, device_name)
        self._attr_native_value = DEFAULT_WARNSCHWELLE_MINUTES

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            value = last_data.native_value
            if value > _LEGACY_SECONDS_VALUE_THRESHOLD:
                # Restored from before this entity switched from seconds to
                # minutes (e.g. the 600s default) - convert rather than
                # restoring an out-of-bounds value like "600 min".
                value = round(value / 60, 1)
            self._attr_native_value = value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
