"""Climate platform for ÖkOfen heating circuits.

Maps the heating circuit's real Betriebsart enum (Aus / Auto / Heizen /
Absenken, read live from the device via formatTexts, same as select.py)
onto Home Assistant's climate model:

    Aus      -> HVACMode.OFF
    Auto     -> HVACMode.AUTO
    Heizen   -> HVACMode.HEAT,  preset_mode = PRESET_NONE
    Absenken -> HVACMode.HEAT,  preset_mode = PRESET_ECO

"Absenken" (setback/reduced temperature) isn't itself a distinct HVAC
mode, so it's represented as a preset on top of HEAT rather than
inventing a mode HA doesn't understand - the same way a real thermostat
firmware would expose a night-setback as a preset.

Target/current temperature reuse the exact same CAPPL parameters as the
existing number/sensor entities for this circuit, so this entity never
diverges from what number.<hk>_raumtemp_heizen and the Raumtemperatur Ist
sensor already show - it's just a different view onto the same data.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PRESET_ECO,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

# Index -> (hvac_mode, preset_mode). Falls back to this fixed order if the
# device doesn't provide formatTexts for betriebsart[0] on older firmware;
# matches the fallback_options already used in select.py for this parameter.
MODE_FALLBACK = ["Aus", "Auto", "Heizen", "Absenken"]


def build_climate_definitions(circuits: Dict[str, List[int]]) -> Dict[str, Dict[str, Any]]:
    """Build one climate entity per heating circuit present on this device."""
    defs: Dict[str, Dict[str, Any]] = {}
    for idx in circuits.get("hk", []):
        base = f"CAPPL:LOCAL.hk[{idx}]"
        label = f"Heizkreis {idx + 1}"
        defs[f"hk{idx}_climate"] = {
            "name": label,
            "mode_parameter": f"{base}.betriebsart[0]",
            "target_parameter": f"{base}.raumtemp_heizen",
            "current_parameter": f"CAPPL:LOCAL.L_hk[{idx}].raumtemp_ist",
        }
    return defs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one climate entity per heating circuit."""
    entry_data = hass.data["oekofen"][config_entry.entry_id]
    api: PellematicAPI = entry_data["api"]
    circuits = entry_data["circuits"]
    definitions = build_climate_definitions(circuits)

    if not definitions:
        return

    parameters: List[str] = []
    for config in definitions.values():
        parameters += [config["mode_parameter"], config["target_parameter"], config["current_parameter"]]

    coordinator = OekofenClimateCoordinator(hass, api, parameters)
    await coordinator.async_config_entry_first_refresh()

    device_name = f"ÖkOfen {config_entry.data[CONF_HOST]}"
    entities = [
        OekofenClimate(coordinator, api, key, config, config_entry.entry_id, device_name)
        for key, config in definitions.items()
    ]
    async_add_entities(entities)


class OekofenClimateCoordinator(DataUpdateCoordinator):
    """Coordinator polling mode/target/current temperature for the climate entities."""

    def __init__(self, hass: HomeAssistant, api: PellematicAPI, parameters: List[str]) -> None:
        self.api = api
        self._parameters = parameters
        super().__init__(
            hass,
            _LOGGER,
            name="ÖkOfen Heizkreis Climate",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self.api.get_data(self._parameters)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error communicating with ÖkOfen device: {err}") from err


class OekofenClimate(CoordinatorEntity, ClimateEntity):
    """A heating circuit, exposed as a standard HA climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        coordinator: OekofenClimateCoordinator,
        api: PellematicAPI,
        key: str,
        config: Dict[str, Any],
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.api = api
        self._mode_parameter = config["mode_parameter"]
        self._target_parameter = config["target_parameter"]
        self._current_parameter = config["current_parameter"]
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = config["name"]
        self._attr_icon = "mdi:radiator"
        self._attr_device_info = {
            "identifiers": {("oekofen", entry_id)},
            "name": device_name,
            "manufacturer": "ÖkOfen",
            "model": "Pellematic",
        }

    def _point(self, parameter: str) -> Optional[Dict[str, Any]]:
        return self.coordinator.data.get(parameter)

    def _mode_options(self) -> List[str]:
        point = self._point(self._mode_parameter)
        format_texts = (point.get("formatTexts") if point else "") or ""
        format_texts = format_texts.strip()
        if format_texts:
            return [text.strip() for text in format_texts.split("|")]
        return MODE_FALLBACK

    def _mode_index(self) -> Optional[int]:
        point = self._point(self._mode_parameter)
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return int(float(point["value"]))
        except (TypeError, ValueError):
            return None

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
        point = self._point(self._target_parameter)
        if not point or point.get("value") in (None, ""):
            return None
        try:
            return round(float(point["value"]) / self._divisor(self._target_parameter), 1)
        except (TypeError, ValueError):
            return None

    @property
    def min_temp(self) -> float:
        point = self._point(self._target_parameter)
        if point:
            try:
                return round(float(point.get("lowerLimit")) / self._divisor(self._target_parameter), 1)
            except (TypeError, ValueError):
                pass
        return 10.0

    @property
    def max_temp(self) -> float:
        point = self._point(self._target_parameter)
        if point:
            try:
                return round(float(point.get("upperLimit")) / self._divisor(self._target_parameter), 1)
            except (TypeError, ValueError):
                pass
        return 28.0

    @property
    def hvac_mode(self) -> Optional[HVACMode]:
        options = self._mode_options()
        index = self._mode_index()
        if index is None or not (0 <= index < len(options)):
            return None
        label = options[index]
        if label == "Aus":
            return HVACMode.OFF
        if label == "Auto":
            return HVACMode.AUTO
        # Both "Heizen" and "Absenken" run the circuit's own heat control;
        # "Absenken" is surfaced as a preset (see preset_mode below).
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> Optional[str]:
        options = self._mode_options()
        index = self._mode_index()
        if index is None or not (0 <= index < len(options)):
            return PRESET_NONE
        return PRESET_ECO if options[index] == "Absenken" else PRESET_NONE

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._mode_parameter in self.coordinator.data

    async def _write_mode(self, label: str) -> None:
        options = self._mode_options()
        if label not in options:
            _LOGGER.warning("Mode '%s' not available in device options %s", label, options)
            return
        await self.api.set_data(self._mode_parameter, options.index(label))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._write_mode("Aus")
        elif hvac_mode == HVACMode.AUTO:
            await self._write_mode("Auto")
        elif hvac_mode == HVACMode.HEAT:
            await self._write_mode("Heizen")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_ECO:
            await self._write_mode("Absenken")
        else:
            await self._write_mode("Heizen")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        divisor = self._divisor(self._target_parameter)
        raw_value = round(temperature * divisor)
        await self.api.set_data(self._target_parameter, raw_value)
        await self.coordinator.async_request_refresh()
