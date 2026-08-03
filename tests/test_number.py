"""Tests for the number platform (number.py)."""
from unittest.mock import AsyncMock

from homeassistant.const import EntityCategory

from custom_components.oekofen.number import OekofenNumber, build_number_definitions

from .conftest import FakeCoordinator, make_point


def test_build_number_definitions_covers_all_circuit_types():
    defs = build_number_definitions({"hk": [0], "ww": [0], "pellematic": [0], "zirkp": [0]})

    assert defs["hk0_raumtemp_heizen"]["parameter"] == "CAPPL:LOCAL.hk[0].raumtemp_heizen"
    assert defs["ww0_wassertemp_soll"]["parameter"] == "CAPPL:LOCAL.ww[0].temp_heizen"
    assert defs["pe0_kesseltemperatur_soll"]["parameter"] == "CAPPL:FA[0].pe_kesseltemperatur_soll"
    assert defs["zirkp0_abschalttemp"]["parameter"] == "CAPPL:LOCAL.zirkp[0].ruecklauftemp_soll"


def test_build_number_definitions_marks_installer_tuning_fields_as_config():
    defs = build_number_definitions({"hk": [0], "ww": [0], "pellematic": [], "zirkp": []})
    for key in (
        "hk0_heizkurve_steigung",
        "hk0_heizkurve_fusspunkt",
        "hk0_vorhaltezeit",
        "hk0_raumfuehlereinfluss",
        "hk0_vorlauftemp_max",
        "hk0_vorlauftemp_min",
    ):
        assert defs[key]["config"] is True

    # User-facing setpoints stay as regular (non-config) entities.
    assert "config" not in defs["hk0_raumtemp_heizen"]
    assert "config" not in defs["ww0_wassertemp_soll"]


def test_config_flag_sets_entity_category():
    config = {"parameter": "P", "name": "N", "icon": None, "config": True}
    entity = OekofenNumber(FakeCoordinator({}), AsyncMock(), "k", config, entry_id="e1", device_name="Test")
    assert entity._attr_entity_category == EntityCategory.CONFIG


def test_no_config_flag_leaves_entity_category_unset():
    config = {"parameter": "P", "name": "N", "icon": None}
    entity = OekofenNumber(FakeCoordinator({}), AsyncMock(), "k", config, entry_id="e1", device_name="Test")
    assert entity._attr_entity_category is None


def test_build_number_definitions_includes_vorlauftemp_per_circuit():
    defs = build_number_definitions({"hk": [0, 1], "ww": [], "pellematic": [], "zirkp": []})
    assert defs["hk0_vorlauftemp_max"]["parameter"] == "CAPPL:LOCAL.hk[0].vorlauftemp_max"
    assert defs["hk0_vorlauftemp_min"]["parameter"] == "CAPPL:LOCAL.hk[0].vorlauftemp_min"
    assert defs["hk1_vorlauftemp_max"]["parameter"] == "CAPPL:LOCAL.hk[1].vorlauftemp_max"
    assert defs["hk1_vorlauftemp_min"]["parameter"] == "CAPPL:LOCAL.hk[1].vorlauftemp_min"


def test_build_number_definitions_empty_for_absent_circuits():
    assert build_number_definitions({"hk": [], "ww": [], "pellematic": [], "zirkp": []}) == {}


def test_build_number_definitions_second_circuit_index():
    defs = build_number_definitions({"hk": [1], "ww": [], "pellematic": [], "zirkp": []})
    assert defs["hk1_raumtemp_heizen"]["parameter"] == "CAPPL:LOCAL.hk[1].raumtemp_heizen"
    assert defs["hk1_raumtemp_heizen"]["name"] == "Heizkreis 2 Raumtemp Heizen"


def _make_entity(coordinator, config, key="hk0_raumtemp_heizen", api=None):
    return OekofenNumber(coordinator, api or AsyncMock(), key, config, entry_id="entry1", device_name="Test")


def test_native_value_applies_divisor():
    config = {"parameter": "P", "name": "N", "icon": None, "temperature": True}
    coord = FakeCoordinator({"P": make_point("190", divisor="10")})
    entity = _make_entity(coord, config)
    assert entity.native_value == 19.0


def test_native_value_none_when_missing_or_blank():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({})
    assert _make_entity(coord, config).native_value is None

    coord = FakeCoordinator({"P": make_point("")})
    assert _make_entity(coord, config).native_value is None


def test_min_max_read_from_device_limits():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({"P": make_point("100", divisor="10", lower_limit="50", upper_limit="400")})
    entity = _make_entity(coord, config)
    assert entity.native_min_value == 5.0
    assert entity.native_max_value == 40.0


def test_min_max_fall_back_to_defaults_when_limits_missing():
    config = {"parameter": "P", "name": "N", "icon": None}
    coord = FakeCoordinator({"P": make_point("100")})
    entity = _make_entity(coord, config)
    assert entity.native_min_value == -50.0
    assert entity.native_max_value == 100.0


def test_available_false_when_parameter_absent_or_coordinator_failed():
    config = {"parameter": "P", "name": "N", "icon": None}
    assert _make_entity(FakeCoordinator({}), config).available is False
    assert _make_entity(
        FakeCoordinator({"P": make_point("1")}, last_update_success=False), config
    ).available is False
    assert _make_entity(FakeCoordinator({"P": make_point("1")}), config).available is True


async def test_async_set_native_value_applies_divisor_and_refreshes():
    config = {"parameter": "P", "name": "N", "icon": None}
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("100", divisor="10")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_native_value(21.5)

    api.set_data.assert_awaited_once_with("P", 21.5, divisor=10)
    assert coord.refresh_calls == 1


async def test_async_set_native_value_no_divisor_when_none_or_one():
    config = {"parameter": "P", "name": "N", "icon": None}
    api = AsyncMock()
    coord = FakeCoordinator({"P": make_point("1", divisor="1")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_native_value(1)

    api.set_data.assert_awaited_once_with("P", 1, divisor=None)


def test_unique_id_and_device_info_use_entry_id():
    config = {"parameter": "P", "name": "N", "icon": None}
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.unique_id == "entry1_hk0_raumtemp_heizen"
    assert entity.device_info["identifiers"] == {("oekofen", "entry1")}
