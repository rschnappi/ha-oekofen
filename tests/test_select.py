"""Tests for the select platform (select.py)."""
from unittest.mock import AsyncMock

import pytest

from custom_components.oekofen.betriebsart import ANLAGE_MODE_PARAMETER
from custom_components.oekofen.select import (
    INSTALLER_WARNING,
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
