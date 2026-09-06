"""Tests for the select platform (select.py)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.oekofen.betriebsart import ANLAGE_MODE_PARAMETER, AUS_MODE_HINWEIS
from custom_components.oekofen.select import (
    HEIZPROGRAMM_OPTIONS,
    INSTALLER_WARNING,
    OekofenHeizprogrammSelect,
    OekofenModeSelect,
    build_select_definitions,
)

from .conftest import FakeCoordinator, make_point


def test_build_select_definitions_marks_installer_locked_fields_with_warning():
    defs = build_select_definitions({"hk": [], "ww": [0], "zirkp": [], "pellematic": []})
    assert defs["ww0_vorrang"]["warning"] == INSTALLER_WARNING
    assert defs["ww0_vorrang"]["name"].startswith("⚠️ ")
    assert defs["ww0_legionellenschutz"]["warning"] == INSTALLER_WARNING
    assert defs["ww0_legionellenschutz"]["name"].startswith("⚠️ ")
    assert "warning" not in defs["ww0_zeitprogramm"]


def test_installer_warning_exposed_as_extra_state_attribute():
    config = {"parameter": "P", "name": "N", "icon": None, "warning": INSTALLER_WARNING}
    entity = OekofenModeSelect(FakeCoordinator({}), AsyncMock(), "k", config, entry_id="e1", device_name="Test")
    assert entity.extra_state_attributes == {"warnhinweis": INSTALLER_WARNING}


def test_no_warning_by_default():
    config = {"parameter": "P", "name": "N", "icon": None}
    entity = OekofenModeSelect(FakeCoordinator({}), AsyncMock(), "k", config, entry_id="e1", device_name="Test")
    assert entity.extra_state_attributes is None


def test_build_select_definitions_always_includes_system_mode():
    defs = build_select_definitions({"hk": [], "ww": [], "zirkp": [], "pellematic": []})
    assert defs["system_mode"]["parameter"] == "CAPPL:LOCAL.anlage_betriebsart"


def test_build_select_definitions_per_circuit():
    defs = build_select_definitions({"hk": [0], "ww": [0], "zirkp": [0], "pellematic": [0]})
    # hk/ww betriebsart is slotted by the current Anlage-Betriebsart, so it
    # has no fixed "parameter" - see betriebsart.py.
    assert defs["hk0_mode"]["betriebsart_base"] == "CAPPL:LOCAL.hk[0]"
    assert "parameter" not in defs["hk0_mode"]
    assert defs["hk0_zeitprogramm"]["parameter"] == "CAPPL:LOCAL.hk[0].aktives_zeitprogramm"
    assert defs["ww0_vorrang"]["parameter"] == "CAPPL:LOCAL.ww[0].prioritaet"
    assert defs["ww0_legionellenschutz"]["parameter"] == "CAPPL:LOCAL.ww[0].legionellen_wochentag"
    # Zirkulationspumpe's mode is NOT installer-gated in the vendor's own
    # config.min.js (anzeigebedingung:null), unlike hk/ww's mode, so it is
    # a plain fixed "parameter" - not slotted, no warning.
    assert defs["zirkp0_mode"]["parameter"] == "CAPPL:LOCAL.zirkp[0].betriebsart"
    assert "warning" not in defs["zirkp0_mode"]
    assert defs["zirkp0_zeitprogramm"]["parameter"] == "CAPPL:LOCAL.zirkp[0].aktives_zeitprogramm"
    # Pellematic's mode is NOT slotted, unlike hk/ww.
    assert defs["pe0_mode"]["parameter"] == "CAPPL:FA[0].betriebsart_fa"


async def test_hk_mode_select_uses_slot_matching_current_anlage_mode():
    """Regression test: Anlage=Auto (slot 1) must read/write betriebsart[1], not [0]."""
    config = build_select_definitions({"hk": [0], "ww": [], "zirkp": [], "pellematic": []})["hk0_mode"]
    api = AsyncMock()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("1"),  # Anlage = Auto
        "CAPPL:LOCAL.hk[0].betriebsart[0]": make_point("2", format_texts="Aus|Auto|Heizen|Absenken"),  # stale
        "CAPPL:LOCAL.hk[0].betriebsart[1]": make_point("0", format_texts="Aus|Auto|Heizen|Absenken"),  # active
    })
    entity = OekofenModeSelect(coord, api, "hk0_mode", config, entry_id="e1", device_name="Test")

    assert entity.current_option == "Aus"

    await entity.async_select_option("Heizen")
    api.set_data.assert_awaited_once_with("CAPPL:LOCAL.hk[0].betriebsart[1]", 2)


def _make_entity(coordinator, config, api=None):
    return OekofenModeSelect(coordinator, api or AsyncMock(), "hk0_mode", config, entry_id="e1", device_name="Test")


def test_extra_state_attributes_hints_when_anlage_is_aus():
    config = build_select_definitions({"hk": [0], "ww": [], "zirkp": [], "pellematic": []})["hk0_mode"]
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("0")})  # Anlage = Aus
    entity = _make_entity(coord, config)
    assert entity.extra_state_attributes == {"hinweis": AUS_MODE_HINWEIS}


def test_extra_state_attributes_none_when_anlage_not_aus():
    config = build_select_definitions({"hk": [0], "ww": [], "zirkp": [], "pellematic": []})["hk0_mode"]
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("1")})  # Anlage = Auto
    entity = _make_entity(coord, config)
    assert entity.extra_state_attributes is None


def test_extra_state_attributes_none_for_unslotted_zirkp_mode():
    config = build_select_definitions({"hk": [], "ww": [], "zirkp": [0], "pellematic": []})["zirkp0_mode"]
    coord = FakeCoordinator({ANLAGE_MODE_PARAMETER: make_point("0")})
    entity = OekofenModeSelect(coord, AsyncMock(), "zirkp0_mode", config, entry_id="e1", device_name="Test")
    assert entity.extra_state_attributes is None


def test_options_prefers_device_formatTexts_over_fallback():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": ["Fallback"]}
    coord = FakeCoordinator({"P": make_point("1", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config)
    assert entity.options == ["Aus", "Auto", "Heizen", "Absenken"]


def test_options_uses_fallback_when_no_formatTexts():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": ["Aus", "Auto"]}
    coord = FakeCoordinator({"P": make_point("0")})
    entity = _make_entity(coord, config)
    assert entity.options == ["Aus", "Auto"]


def test_current_option_maps_index_to_label():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": []}
    coord = FakeCoordinator({"P": make_point("2", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config)
    assert entity.current_option == "Heizen"


def test_current_option_none_when_index_out_of_range():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": []}
    coord = FakeCoordinator({"P": make_point("99", format_texts="Aus|Auto")})
    entity = _make_entity(coord, config)
    assert entity.current_option is None


def test_current_option_none_when_missing():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": []}
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.current_option is None


async def test_async_select_option_writes_matching_index():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": []}
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("0", format_texts="Aus|Auto|Heizen|Absenken")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_select_option("Heizen")

    api.set_data.assert_awaited_once_with("P", 2)
    assert coord.refresh_calls == 1


async def test_async_select_option_rejects_unknown_option():
    config = {"parameter": "P", "name": "N", "icon": None, "fallback_options": []}
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("0", format_texts="Aus|Auto")})
    entity = _make_entity(coord, config, api=api)

    with pytest.raises(ValueError):
        await entity.async_select_option("Nonexistent")

    api.set_data.assert_not_awaited()


# --- OekofenHeizprogrammSelect (Sommer/Übergang/Winter season switch) -------

_ZEIT_HK = "CAPPL:LOCAL.hk[0].aktives_zeitprogramm"
_ZEIT_WW = "CAPPL:LOCAL.ww[0].aktives_zeitprogramm"


def _make_heizprogramm_entity(coordinator, api=None, zeitprogramm_parameters=None):
    return OekofenHeizprogrammSelect(
        coordinator,
        api or AsyncMock(),
        entry_id="e1",
        device_name="Test",
        zeitprogramm_parameters=zeitprogramm_parameters or [_ZEIT_HK, _ZEIT_WW],
    )


def test_heizprogramm_options_are_fixed():
    entity = _make_heizprogramm_entity(FakeCoordinator({}))
    assert entity.options == HEIZPROGRAMM_OPTIONS == ["Sommer", "Übergang", "Winter"]


async def test_heizprogramm_winter_sets_anlage_auto_and_all_zeitprogramme_zeit_1():
    api = AsyncMock()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("1", format_texts="Aus|Auto|Warmwasser"),
        _ZEIT_HK: make_point("1", format_texts="Zeit 1|Zeit 2"),
        _ZEIT_WW: make_point("0", format_texts="Zeit 1|Zeit 2"),
    })
    entity = _make_heizprogramm_entity(coord, api=api)
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("Winter")

    api.set_data.assert_any_await(ANLAGE_MODE_PARAMETER, 1)  # Auto
    api.set_data.assert_any_await(_ZEIT_HK, 0)  # Zeit 1
    api.set_data.assert_any_await(_ZEIT_WW, 0)  # Zeit 1
    assert entity.current_option == "Winter"
    assert coord.refresh_calls == 1


async def test_heizprogramm_uebergang_sets_anlage_auto_and_all_zeitprogramme_zeit_2():
    api = AsyncMock()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("2", format_texts="Aus|Auto|Warmwasser"),
        _ZEIT_HK: make_point("0", format_texts="Zeit 1|Zeit 2"),
        _ZEIT_WW: make_point("0", format_texts="Zeit 1|Zeit 2"),
    })
    entity = _make_heizprogramm_entity(coord, api=api)
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("Übergang")

    api.set_data.assert_any_await(ANLAGE_MODE_PARAMETER, 1)  # Auto
    api.set_data.assert_any_await(_ZEIT_HK, 1)  # Zeit 2
    api.set_data.assert_any_await(_ZEIT_WW, 1)  # Zeit 2
    assert entity.current_option == "Übergang"


async def test_heizprogramm_sommer_sets_anlage_warmwasser_and_leaves_zeitprogramme_untouched():
    api = AsyncMock()
    coord = FakeCoordinator({
        ANLAGE_MODE_PARAMETER: make_point("1", format_texts="Aus|Auto|Warmwasser"),
        _ZEIT_HK: make_point("0", format_texts="Zeit 1|Zeit 2"),
        _ZEIT_WW: make_point("0", format_texts="Zeit 1|Zeit 2"),
    })
    entity = _make_heizprogramm_entity(coord, api=api)
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("Sommer")

    api.set_data.assert_awaited_once_with(ANLAGE_MODE_PARAMETER, 2)  # Warmwasser, only call
    assert entity.current_option == "Sommer"


async def test_heizprogramm_restores_last_option_across_restart():
    entity = _make_heizprogramm_entity(FakeCoordinator({}))
    entity.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="Winter"))

    with patch.object(CoordinatorEntity, "async_added_to_hass", AsyncMock()):
        await entity.async_added_to_hass()

    assert entity.current_option == "Winter"


async def test_heizprogramm_ignores_invalid_restored_state():
    entity = _make_heizprogramm_entity(FakeCoordinator({}))
    entity.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="unavailable"))

    with patch.object(CoordinatorEntity, "async_added_to_hass", AsyncMock()):
        await entity.async_added_to_hass()

    assert entity.current_option is None
