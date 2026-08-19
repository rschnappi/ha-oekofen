"""Climate platform for ÖkOfen heating circuits and warm-water circuits.

Maps each circuit's real Betriebsart enum (read live from the device via
formatTexts, same as select.py) onto Home Assistant's climate model via a
per-circuit mode_map: {device label: (hvac_mode, preset_mode)}.

Heizkreis (hk):  Aus / Auto / Heizen / Absenken
    Aus      -> HVACMode.OFF
    Auto     -> HVACMode.AUTO
    Heizen   -> HVACMode.HEAT,  preset_mode = PRESET_NONE
    Absenken -> HVACMode.HEAT,  preset_mode = "Absenken"

"Absenken" (setback/reduced temperature) isn't itself a distinct HVAC
mode, so it's represented as a preset on top of HEAT rather than
inventing a mode HA doesn't understand.

Warmwasser (ww):  Aus / Auto / Ein
    Aus  -> HVACMode.OFF
    Auto -> HVACMode.AUTO
    Ein  -> HVACMode.HEAT   (no preset - this circuit has no setback mode)

Target/current temperature reuse the exact same CAPPL parameters as the
existing number/sensor entities for each circuit, so this entity never
diverges from what the number/sensor entities already show - it's just a
different, standard-climate-domain view onto the same data.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PRESET_BOOST,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .betriebsart import (
    ANLAGE_MODE_PARAMETER,
    AUS_MODE_HINWEIS,
    active_betriebsart_slot,
    betriebsart_parameter,
    betriebsart_slot_parameters,
)
from .coordinator import OekofenCoordinator
from .entity_helpers import build_device_info, parameter_available
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

# Custom preset label matching the device's own wording exactly, instead of
# HA's generic built-in PRESET_ECO ("Eco") which would be a translation
# mismatch for what the device itself calls "Absenken".
PRESET_ABSENKEN = "Absenken"

# device label -> (hvac_mode, preset_mode)
HK_MODE_MAP: Dict[str, Tuple[HVACMode, str]] = {
    "Aus": (HVACMode.OFF, PRESET_NONE),
    "Auto": (HVACMode.AUTO, PRESET_NONE),
    "Heizen": (HVACMode.HEAT, PRESET_NONE),
    "Absenken": (HVACMode.HEAT, PRESET_ABSENKEN),
}
HK_MODE_FALLBACK = ["Aus", "Auto", "Heizen", "Absenken"]

WW_MODE_MAP: Dict[str, Tuple[HVACMode, str]] = {
    "Aus": (HVACMode.OFF, PRESET_NONE),
    "Auto": (HVACMode.AUTO, PRESET_NONE),
    "Ein": (HVACMode.HEAT, PRESET_NONE),
}
WW_MODE_FALLBACK = ["Aus", "Auto", "Ein"]

# Pellematic (boiler unit) uses the exact same three-state model as Warmwasser.
PE_MODE_MAP: Dict[str, Tuple[HVACMode, str]] = {
    "Aus": (HVACMode.OFF, PRESET_NONE),
    "Auto": (HVACMode.AUTO, PRESET_NONE),
    "Ein": (HVACMode.HEAT, PRESET_NONE),
}
PE_MODE_FALLBACK = ["Aus", "Auto", "Ein"]


def build_climate_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build one climate entity per heating circuit, warm-water circuit and Pellematic unit."""
    defs: Dict[str, Dict[str, Any]] = {}

    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_climate"] = {
            "name": label,
            "icon": "mdi:radiator",
            "betriebsart_base": base,
            "target_parameter": f"{base}.raumtemp_heizen",
            "current_parameter": f"CAPPL:LOCAL.L_hk[{idx}].raumtemp_ist",
            "mode_map": HK_MODE_MAP,
            "mode_fallback": HK_MODE_FALLBACK,
            "default_min_temp": 10.0,
            "default_max_temp": 28.0,
        }

    for idx in circuits.get("ww", []):
        base = f"CAPPL:LOCAL.ww[{idx}]"
        label = f"Warmwasser {idx + 1}"
        defs[f"ww{idx}_climate"] = {
            "name": label,
            "icon": "mdi:water-boiler",
            "betriebsart_base": base,
            "target_parameter": f"{base}.temp_heizen",
            "current_parameter": f"CAPPL:LOCAL.L_ww[{idx}].einschaltfuehler_ist",
            "mode_map": WW_MODE_MAP,
            "mode_fallback": WW_MODE_FALLBACK,
            "default_min_temp": 30.0,
            "default_max_temp": 65.0,
            # "Einmal Aufbereiten": a one-off reheat cycle, independent of
            # betriebsart. Exposed as PRESET_BOOST here in addition to (not
            # instead of) the existing standalone switch entity.
            "boost_parameter": f"{base}.einmal_aufbereiten",
        }

    for idx in circuits.get("pellematic", []):
        base = f"CAPPL:FA[{idx}]"
        label = f"Pellematic {idx + 1}"
        defs[f"pe{idx}_climate"] = {
            "name": label,
            "icon": "mdi:fire",
            "mode_parameter": f"{base}.betriebsart_fa",
            "target_parameter": f"{base}.pe_kesseltemperatur_soll",
            # On "Smart" firmware (L_pe_schnecke_sauganlage==4) the device
            # ignores pe_kesseltemperatur_soll and regulates off
            # frischwasser_soll_temp instead (config.min.js gates the
            # former to "!= 4" in the vendor's own menu) - same
            # dual-firmware split number.py already handles for this same
            # setpoint. Read/write picks whichever one the device actually
            # returns real data for - see _active_target_parameter().
            "target_parameter_smart": f"{base}.frischwasser_soll_temp",
            "current_parameter": f"{base}.L_kesseltemperatur",
            "mode_map": PE_MODE_MAP,
            "mode_fallback": PE_MODE_FALLBACK,
            "default_min_temp": 40.0,
            "default_max_temp": 90.0,
        }

    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one climate entity per heating/warm-water circuit."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    coordinator = entry_data["coordinator"]
    definitions = build_climate_definitions(circuits)

    if not definitions:
        return

    parameters: List[str] = []
    for config in definitions.values():
        if config.get("betriebsart_base"):
            parameters += betriebsart_slot_parameters(config["betriebsart_base"])
        else:
            parameters.append(config["mode_parameter"])
        parameters += [config["target_parameter"], config["current_parameter"]]
        if config.get("target_parameter_smart"):
            parameters.append(config["target_parameter_smart"])
        if config.get("boost_parameter"):
            parameters.append(config["boost_parameter"])
    if ANLAGE_MODE_PARAMETER not in parameters:
        parameters.append(ANLAGE_MODE_PARAMETER)
    coordinator.add_parameters(parameters)

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenClimate(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenClimate(CoordinatorEntity, ClimateEntity):
    """A heating or warm-water circuit, exposed as a standard HA climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

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
        self._betriebsart_base: Optional[str] = config.get("betriebsart_base")
        self._mode_parameter: Optional[str] = config.get("mode_parameter")
        self._target_parameter = config["target_parameter"]
        self._target_parameter_smart: Optional[str] = config.get("target_parameter_smart")
        self._current_parameter = config["current_parameter"]
        self._mode_map: Dict[str, Tuple[HVACMode, str]] = config["mode_map"]
        self._mode_fallback: List[str] = config["mode_fallback"]
        self._default_min_temp = config["default_min_temp"]
        self._default_max_temp = config["default_max_temp"]
        self._boost_parameter: Optional[str] = config.get("boost_parameter")

        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = config["icon"]

        hvac_modes = sorted({mode for mode, _preset in self._mode_map.values()}, key=lambda m: m.value)
        # Keep OFF/AUTO/HEAT in a sensible fixed order rather than alpha sort.
        order = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]
        self._attr_hvac_modes = [m for m in order if m in hvac_modes]

        presets = sorted({preset for _mode, preset in self._mode_map.values() if preset != PRESET_NONE})
        if self._boost_parameter:
            presets = presets + [PRESET_BOOST]
        features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        # Always assign _attr_preset_modes (None when there are no presets):
        # ClimateEntity's preset_modes property reads this attribute
        # unconditionally, so leaving it unset for circuits without presets
        # (e.g. Warmwasser) raises AttributeError instead of returning None.
        if presets:
            self._attr_preset_modes = [PRESET_NONE] + presets
            features |= ClimateEntityFeature.PRESET_MODE
        else:
            self._attr_preset_modes = None
        self._attr_supported_features = features

        self._attr_device_info = build_device_info(entry_id, device_name)

    def _point(self, parameter: str) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(parameter)

    def _mode_parameter_now(self) -> str:
        if self._betriebsart_base:
            return betriebsart_parameter(self._betriebsart_base, self.coordinator.data)
        return self._mode_parameter

    def _mode_options(self) -> List[str]:
        point = self._point(self._mode_parameter_now())
        format_texts = (point.get("formatTexts") if point else "") or ""
        format_texts = format_texts.strip()
        if format_texts:
            return [text.strip() for text in format_texts.split("|")]
        return self._mode_fallback

    def _mode_label(self) -> Optional[str]:
        point = self._point(self._mode_parameter_now())
        if not point or point.get("value") in (None, ""):
            return None
        try:
            index = int(float(point["value"]))
        except (TypeError, ValueError):
            return None
        options = self._mode_options()
        if 0 <= index < len(options):
            return options[index]
        return None

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        if self._betriebsart_base and active_betriebsart_slot(self.coordinator.data) == 0:
            return {"hinweis": AUS_MODE_HINWEIS}
        return None

    def _active_target_parameter(self) -> str:
        """Pick whichever setpoint parameter this boiler's firmware actually
        uses (see target_parameter_smart's definition-site comment) - the
        device only ever returns real data for the applicable one, so a
        missing/empty value on the classic parameter means this is a
        Smart-firmware boiler."""
        if self._target_parameter_smart:
            point = self._point(self._target_parameter)
            if not point or point.get("value") in (None, ""):
                return self._target_parameter_smart
        return self._target_parameter

    def _divisor(self, parameter: str) -> float:
        point = self._point(parameter)
        if not point:
            return 1.0
        try:
            divisor = float(point.get("divisor") or 1)
            return divisor if divisor > 0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    @property
    def current_temperature(self) -> Optional[float]:
        point = self._point(self._current_parameter)
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return round(float(point["value"]) / self._divisor(self._current_parameter), 1)
        except (TypeError, ValueError):
            return None

    @property
    def target_temperature(self) -> Optional[float]:
        parameter = self._active_target_parameter()
        point = self._point(parameter)
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return round(float(point["value"]) / self._divisor(parameter), 1)
        except (TypeError, ValueError):
            return None

    @property
    def min_temp(self) -> float:
        parameter = self._active_target_parameter()
        point = self._point(parameter)
        if point:
            try:
                return round(float(point.get("lowerLimit")) / self._divisor(parameter), 1)
            except (TypeError, ValueError):
                pass
        return self._default_min_temp

    @property
    def max_temp(self) -> float:
        parameter = self._active_target_parameter()
        point = self._point(parameter)
        if point:
            try:
                return round(float(point.get("upperLimit")) / self._divisor(parameter), 1)
            except (TypeError, ValueError):
                pass
        return self._default_max_temp

    @property
    def hvac_mode(self) -> Optional[HVACMode]:
        label = self._mode_label()
        if label is None:
            return None
        mapped = self._mode_map.get(label)
        return mapped[0] if mapped else None

    def _is_boost_active(self) -> bool:
        if not self._boost_parameter:
            return False
        point = self._point(self._boost_parameter)
        if not point or point.get("value") in (None, ""):
            return False
        try:
            return int(float(point["value"])) == 1
        except (TypeError, ValueError):
            return False

    @property
    def preset_mode(self) -> Optional[str]:
        if self._is_boost_active():
            return PRESET_BOOST
        label = self._mode_label()
        if label is None:
            return PRESET_NONE
        mapped = self._mode_map.get(label)
        return mapped[1] if mapped else PRESET_NONE

    @property
    def available(self) -> bool:
        return parameter_available(self.coordinator, self._mode_parameter_now())

    async def _write_label(self, label: str) -> None:
        options = self._mode_options()
        if label not in options:
            _LOGGER.warning("Mode '%s' not available in device options %s", label, options)
            return
        await self.api.set_data(self._mode_parameter_now(), options.index(label))
        await self.coordinator.async_request_refresh()

    def _label_for(self, hvac_mode: Optional[HVACMode] = None, preset_mode: Optional[str] = None) -> Optional[str]:
        """Find the device label matching the requested hvac_mode and/or preset_mode."""
        target_mode = hvac_mode if hvac_mode is not None else self.hvac_mode
        target_preset = preset_mode if preset_mode is not None else PRESET_NONE
        for label, (mode, preset) in self._mode_map.items():
            if mode == target_mode and preset == target_preset:
                return label
        # Fall back to any label matching just the mode, ignoring preset.
        for label, (mode, _preset) in self._mode_map.items():
            if mode == target_mode:
                return label
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        label = self._label_for(hvac_mode=hvac_mode, preset_mode=PRESET_NONE)
        if label:
            await self._write_label(label)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self._boost_parameter and preset_mode == PRESET_BOOST:
            await self.api.set_data(self._boost_parameter, 1)
            await self.coordinator.async_request_refresh()
            return

        if self._boost_parameter and self._is_boost_active() and preset_mode == PRESET_NONE:
            await self.api.set_data(self._boost_parameter, 0)
            await self.coordinator.async_request_refresh()
            return

        # Presets apply on top of HEAT in this device's model.
        label = self._label_for(hvac_mode=HVACMode.HEAT, preset_mode=preset_mode)
        if label:
            await self._write_label(label)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        parameter = self._active_target_parameter()
        divisor = self._divisor(parameter)
        raw_value = round(temperature * divisor)
        await self.api.set_data(parameter, raw_value)
        await self.coordinator.async_request_refresh()
