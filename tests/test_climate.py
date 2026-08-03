"""Tests for the climate platform (climate.py)."""
from unittest.mock import AsyncMock

from homeassistant.components.climate import PRESET_BOOST, PRESET_NONE, HVACMode

from custom_components.oekofen.betriebsart import ANLAGE_MODE_PARAMETER, AUS_MODE_HINWEIS
from custom_components.oekofen.climate import (
    HK_MODE_MAP,
    PE_MODE_MAP,
    WW_MODE_MAP,
    OekofenClimate,
    build_climate_definitions,
)

from .conftest import FakeCoordinator, make_point


def test_build_climate_definitions_one_per_circuit():
    defs = build_climate_definitions({"hk": [0], "ww": [0], "pellematic": [0]})
    assert defs["hk0_climate"]["betriebsart_base"] == "CAPPL:LOCAL.hk[0]"
    assert defs["hk0_climate"]["target_parameter"] == "CAPPL:LOCAL.hk[0].raumtemp_heizen"
    assert defs["hk0_climate"]["current_parameter"] == "CAPPL:LOCAL.L_hk[0].raumtemp_ist"
    assert defs["hk0_climate"]["mode_map"] is HK_MODE_MAP

    assert defs["ww0_climate"]["betriebsart_base"] == "CAPPL:LOCAL.ww[0]"
    assert defs["ww0_climate"]["target_parameter"] == "CAPPL:LOCAL.ww[0].temp_heizen"
    assert defs["ww0_climate"]["mode_map"] is WW_MODE_MAP

    # Pellematic's mode is NOT slotted by Anlage-Betriebsart, unlike hk/ww.
    assert "betriebsart_base" not in defs["pe0_climate"]
    assert defs["pe0_climate"]["mode_parameter"] == "CAPPL:FA[0].betriebsart_fa"
    assert defs["pe0_climate"]["target_parameter"] == "CAPPL:FA[0].pe_kesseltemperatur_soll"
    assert defs["pe0_climate"]["current_parameter"] == "CAPPL:FA[0].L_kesseltemperatur"
    assert defs["pe0_climate"]["mode_map"] is PE_MODE_MAP


def _hk_config():
    return build_climate_definitions({"hk": [0], "ww": []})["hk0_climate"]


def _ww_config():
    return build_climate_definitions({"hk": [], "ww": [0]})["ww0_climate"]


def _pe_config():
    return build_climate_definitions({"hk": [], "ww": [], "pellematic": [0]})["pe0_climate"]


def _make_entity(coordinator, config, key="hk0_climate", api=None):
    return OekofenClimate(coordinator, api or AsyncMock(), key, config, entry_id="e1", device_name="Test")


def _mode_param(config, slot=0):
    return f"{config['betriebsart_base']}.betriebsart[{slot}]"


def test_hvac_modes_are_off_auto_heat_in_order():
    entity = _make_entity(FakeCoordinator({}), _hk_config())
    assert entity.hvac_modes == [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]


def test_hk_preset_modes_include_absenken():
    entity = _make_entity(FakeCoordinator({}), _hk_config())
    assert entity.preset_modes == [PRESET_NONE, "Absenken"]


def test_ww_has_no_mode_map_presets_but_has_boost():
    entity = _make_entity(FakeCoordinator({}), _ww_config(), key="ww0_climate")
    assert entity.preset_modes == [PRESET_NONE, PRESET_BOOST]


def test_build_climate_definitions_ww_has_boost_parameter():
    defs = build_climate_definitions({"hk": [0], "ww": [0]})
    assert defs["ww0_climate"]["boost_parameter"] == "CAPPL:LOCAL.ww[0].einmal_aufbereiten"
    assert "boost_parameter" not in defs["hk0_climate"]


def test_preset_mode_boost_when_active():
    config = _ww_config()
    coord = FakeCoordinator({config["boost_parameter"]: make_point("1")})
    entity = _make_entity(coord, config, key="ww0_climate")
    assert entity.preset_mode == PRESET_BOOST


def test_preset_mode_falls_back_to_mode_map_when_boost_inactive():
    config = _ww_config()
    coord = FakeCoordinator({
        config["boost_parameter"]: make_point("0"),
        _mode_param(config): make_point("2", format_texts="Aus|Auto|Ein"),
    })
    entity = _make_entity(coord, config, key="ww0_climate")
    assert entity.preset_mode == PRESET_NONE


async def test_async_set_preset_mode_boost_writes_boost_parameter():
    config = _ww_config()
    api = AsyncMock()
    coord = FakeCoordinator({config["boost_parameter"]: make_point("0")})
    entity = _make_entity(coord, config, key="ww0_climate", api=api)

    await entity.async_set_preset_mode(PRESET_BOOST)

    api.set_data.assert_awaited_once_with(config["boost_parameter"], 1)
    assert coord.refresh_calls == 1


async def test_async_set_preset_mode_none_cancels_active_boost():
    config = _ww_config()
    api = AsyncMock()
    coord = FakeCoordinator({config["boost_parameter"]: make_point("1")})
    entity = _make_entity(coord, config, key="ww0_climate", api=api)

    await entity.async_set_preset_mode(PRESET_NONE)

    api.set_data.assert_awaited_once_with(config["boost_parameter"], 0)
    assert coord.refresh_calls == 1


def test_pellematic_has_no_presets_and_no_boost_parameter():
    entity = _make_entity(FakeCoordinator({}), _pe_config(), key="pe0_climate")
    assert entity.preset_modes is None
    assert entity._boost_parameter is None


def test_pellematic_hvac_mode_for_ein():
    config = _pe_config()
    coord = FakeCoordinator({config["mode_parameter"]: make_point("2", format_texts="Aus|Auto|Ein")})
    entity = _make_entity(coord, config, key="pe0_climate")
    assert entity.hvac_mode == HVACMode.HEAT


async def test_pellematic_async_set_temperature_writes_regeltemperatur():
    config = _pe_config()
    api = AsyncMock()
    coord = FakeCoordinator({config["target_parameter"]: make_point("650", divisor="10")})
    entity = _make_entity(coord, config, key="pe0_climate", api=api)

    await entity.async_set_temperature(temperature=68.0)

    api.set_data.assert_awaited_once_with(config["target_parameter"], 680)
    assert coord.refresh_calls == 1


def test_hvac_mode_and_preset_for_heizen():
    config = _hk_config()
    coord = FakeCoordinator({_mode_param(config): make_point("2", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config)
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.preset_mode == PRESET_NONE


def test_hvac_mode_and_preset_for_absenken():
    config = _hk_config()
    coord = FakeCoordinator({_mode_param(config): make_point("3", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config)
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.preset_mode == "Absenken"


def test_hvac_mode_uses_slot_matching_current_anlage_mode():
    """Regression test: Anlage=Auto (slot 1) must read betriebsart[1], not [0]."""
    config = _hk_config()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("1"),  # Anlage = Auto
        _mode_param(config, slot=0): make_point("2", format_texts="Aus|Auto|Heizen|Absenken"),  # stale/inactive
        _mode_param(config, slot=1): make_point("0", format_texts="Aus|Auto|Heizen|Absenken"),  # active: "Aus"
    })
    entity = _make_entity(coord, config)
    assert entity.hvac_mode == HVACMode.OFF


def test_hvac_mode_none_when_unavailable():
    config = _hk_config()
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.hvac_mode is None
    assert entity.preset_mode == PRESET_NONE


def test_current_and_target_temperature_apply_divisor():
    config = _hk_config()
    coord = FakeCoordinator({
        config["current_parameter"]: make_point("235", divisor="10"),
        config["target_parameter"]: make_point("190", divisor="10", lower_limit="100", upper_limit="280"),
    })
    entity = _make_entity(coord, config)
    assert entity.current_temperature == 23.5
    assert entity.target_temperature == 19.0
    assert entity.min_temp == 10.0
    assert entity.max_temp == 28.0


def test_min_max_temp_fall_back_to_circuit_defaults():
    config = _hk_config()
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.min_temp == 10.0
    assert entity.max_temp == 28.0


async def test_async_set_hvac_mode_writes_heizen():
    config = _hk_config()
    api = AsyncMock()
    coord = FakeCoordinator({_mode_param(config): make_point("1", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_hvac_mode(HVACMode.HEAT)

    api.set_data.assert_awaited_once_with(_mode_param(config), 2)  # index of "Heizen"


async def test_async_set_preset_mode_absenken_writes_correct_index():
    config = _hk_config()
    api = AsyncMock()
    coord = FakeCoordinator({_mode_param(config): make_point("1", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_preset_mode("Absenken")

    api.set_data.assert_awaited_once_with(_mode_param(config), 3)  # index of "Absenken"


async def test_async_set_hvac_mode_writes_to_slot_matching_current_anlage_mode():
    config = _hk_config()
    api = AsyncMock()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("2"),  # Anlage = Warmwasser -> slot 2
        _mode_param(config, slot=2): make_point("1", format_texts="Aus|Auto|Heizen|Absenken"),
    })
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_hvac_mode(HVACMode.HEAT)

    api.set_data.assert_awaited_once_with(_mode_param(config, slot=2), 2)


async def test_async_set_temperature_applies_divisor():
    config = _hk_config()
    api = AsyncMock()
    coord = FakeCoordinator({config["target_parameter"]: make_point("190", divisor="10")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_temperature(temperature=21.0)

    api.set_data.assert_awaited_once_with(config["target_parameter"], 210)
    assert coord.refresh_calls == 1


async def test_async_set_temperature_noop_without_temperature_kwarg():
    config = _hk_config()
    api = AsyncMock()
    entity = _make_entity(FakeCoordinator({}), config, api=api)

    await entity.async_set_temperature(some_other_kwarg=1)

    api.set_data.assert_not_awaited()


def test_available_false_when_mode_parameter_missing():
    config = _hk_config()
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.available is False


def test_extra_state_attributes_hints_when_anlage_is_aus():
    config = _hk_config()
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("0")})  # Anlage = Aus
    entity = _make_entity(coord, config)
    assert entity.extra_state_attributes == {"hinweis": AUS_MODE_HINWEIS}


def test_extra_state_attributes_none_when_anlage_not_aus():
    config = _hk_config()
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("1")})  # Anlage = Auto
    entity = _make_entity(coord, config)
    assert entity.extra_state_attributes is None


def test_extra_state_attributes_none_for_unslotted_pellematic():
    config = _pe_config()
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("0")})
    entity = _make_entity(coord, config, key="pe0_climate")
    assert entity.extra_state_attributes is None
