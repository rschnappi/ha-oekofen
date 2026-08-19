"""Tests for sensor.py: OekofenSensor's own value/availability logic, and
the Störmelderelais (fault relay) notification watcher."""
from unittest.mock import MagicMock, patch

from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.oekofen.sensor import (
    FAULT_RELAY_PARAMETER,
    OekofenIntegrationVersion,
    OekofenSensor,
    _is_relay_active,
    _register_fault_relay_watcher,
    build_sensor_definitions,
)

from .conftest import FakeCoordinator, make_point


def _make_sensor(entity_category=None):
    config = {"parameter": "P", "name": "N"}
    if entity_category is not None:
        config["entity_category"] = entity_category
    return OekofenSensor(FakeCoordinator({}), "k", config, device_name="Test", entry_id="e1")


def _sensor(coordinator, config=None, sensor_key="k"):
    config = config or {"parameter": "P", "name": "N"}
    return OekofenSensor(coordinator, sensor_key, config, device_name="Test", entry_id="e1")


def test_entity_category_diagnostic_is_applied():
    assert _make_sensor("diagnostic")._attr_entity_category == EntityCategory.DIAGNOSTIC


def test_entity_category_config_is_applied():
    assert _make_sensor("config")._attr_entity_category == EntityCategory.CONFIG


def test_entity_category_absent_by_default():
    assert _make_sensor()._attr_entity_category is None


class ListenerCoordinator:
    """Minimal coordinator stub exposing .data and .async_add_listener()."""

    def __init__(self, data=None):
        self.data = data or {}
        self._listeners = []

    def async_add_listener(self, callback):
        self._listeners.append(callback)
        return lambda: None

    def fire(self):
        for listener in self._listeners:
            listener()


def test_is_relay_active_parses_numeric_values():
    assert _is_relay_active("0") is False
    assert _is_relay_active("1") is True
    assert _is_relay_active("") is False
    assert _is_relay_active(None) is False
    assert _is_relay_active("not-a-number") is False


def test_watcher_creates_notification_when_relay_activates():
    coord = ListenerCoordinator({FAULT_RELAY_PARAMETER: make_point("0")})
    hass = MagicMock()

    with patch("custom_components.oekofen.sensor.persistent_notification") as mock_pn:
        _register_fault_relay_watcher(hass, coord, "entry1")
        mock_pn.async_create.assert_not_called()

        coord.data[FAULT_RELAY_PARAMETER] = make_point("1")
        coord.fire()

        mock_pn.async_create.assert_called_once()
        _, kwargs = mock_pn.async_create.call_args
        assert kwargs["notification_id"] == "oekofen_stoermelderelais_entry1"


def test_watcher_dismisses_notification_when_relay_clears():
    coord = ListenerCoordinator({FAULT_RELAY_PARAMETER: make_point("1")})
    hass = MagicMock()

    with patch("custom_components.oekofen.sensor.persistent_notification") as mock_pn:
        _register_fault_relay_watcher(hass, coord, "entry1")
        mock_pn.async_create.assert_called_once()

        coord.data[FAULT_RELAY_PARAMETER] = make_point("0")
        coord.fire()

        mock_pn.async_dismiss.assert_called_once_with(hass, "oekofen_stoermelderelais_entry1")


def test_integration_version_reads_manifest_and_is_diagnostic():
    entity = OekofenIntegrationVersion("e1", "Test")
    assert entity.native_value  # non-empty version string from manifest.json
    assert entity._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert entity.unique_id == "e1_integration_version"


def test_watcher_does_not_repeat_notification_while_still_active():
    coord = ListenerCoordinator({FAULT_RELAY_PARAMETER: make_point("1")})
    hass = MagicMock()

    with patch("custom_components.oekofen.sensor.persistent_notification") as mock_pn:
        _register_fault_relay_watcher(hass, coord, "entry1")
        assert mock_pn.async_create.call_count == 1

        coord.fire()
        coord.fire()

        assert mock_pn.async_create.call_count == 1


# --- build_sensor_definitions (Pellematic/Heizkreis/Warmwasser scaling) ---

def test_single_circuit_reproduces_original_bare_keys_and_names():
    """Default single-circuit install (the only shape live-tested so far)
    must come out byte-for-byte identical to the pre-refactor hardcoded
    dict, so existing entity_ids/history are untouched."""
    defs = build_sensor_definitions({"hk": [0], "ww": [0], "pellematic": [0]})

    assert len(defs) == 55
    assert defs["boiler_status"]["parameter"] == "CAPPL:FA[0].L_kesselstatus"
    assert defs["boiler_status"]["name"] == "Boiler Status"
    assert defs["pellematic_mode"]["parameter"] == "CAPPL:FA[0].betriebsart_fa"
    assert defs["hk1_flow_temperature"]["parameter"] == "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist"
    assert defs["hk1_flow_temperature"]["name"] == "HK1 Flow Temperature"
    assert defs["ww1_temperature"]["parameter"] == "CAPPL:LOCAL.L_ww[0].einschaltfuehler_ist"
    assert defs["ww1_temperature"]["name"] == "Hot Water Temperature"
    # Non-circuit sensors always present regardless of circuits.
    assert defs["system_mode"]["parameter"] == "CAPPL:LOCAL.anlage_betriebsart"
    assert defs["supply_pump"]["parameter"] == "CAPPL:LOCAL.L_zubrp[0].pumpe"
    assert defs["buffer_pump"]["parameter"] == "CAPPL:LOCAL.L_pu[0].pumpe"


def test_second_pellematic_unit_gets_numbered_key_and_parameter():
    defs = build_sensor_definitions({"hk": [0], "ww": [0], "pellematic": [0, 1]})
    assert "boiler_status" in defs  # first unit keeps its bare key
    assert defs["pe2_boiler_status"]["parameter"] == "CAPPL:FA[1].L_kesselstatus"
    assert defs["pe2_boiler_status"]["name"] == "Pellematic 2 Boiler Status"


def test_third_heating_circuit_uses_its_real_device_index_not_list_position():
    """circuits['hk'] holds actual device slot indices, not a dense
    0..n range - hk[2] present without hk[1] must produce hk3_*, matching
    the idx+1 convention climate.py/number.py/select.py already use."""
    defs = build_sensor_definitions({"hk": [0, 2], "ww": [0], "pellematic": [0]})
    assert defs["hk3_flow_temperature"]["parameter"] == "CAPPL:LOCAL.L_hk[2].vorlauftemp_ist"
    assert defs["hk3_flow_temperature"]["name"] == "HK3 Flow Temperature"


def test_second_hot_water_circuit_gets_numbered_key_and_name():
    defs = build_sensor_definitions({"hk": [0], "ww": [0, 1], "pellematic": [0]})
    assert defs["ww1_temperature"]["name"] == "Hot Water Temperature"  # unchanged
    assert defs["ww2_temperature"]["parameter"] == "CAPPL:LOCAL.L_ww[1].einschaltfuehler_ist"
    assert defs["ww2_temperature"]["name"] == "Hot Water 2 Temperature"
    assert defs["ww2_pump"]["name"] == "Hot Water 2 Pump"


def test_missing_circuit_type_falls_back_to_index_zero():
    """entry_data['circuits'] always comes from discovery.py, but the
    builder shouldn't hard-crash if a key happens to be absent."""
    defs = build_sensor_definitions({})
    assert "boiler_status" in defs
    assert "hk1_flow_temperature" in defs
    assert "ww1_temperature" in defs


# --- native_value ---------------------------------------------------------

def test_native_value_none_when_parameter_missing():
    entity = _sensor(FakeCoordinator({}))
    assert entity.native_value is None


def test_native_value_none_when_value_is_none_or_blank():
    coord = FakeCoordinator({"P": make_point(None)})
    assert _sensor(coord).native_value is None

    coord = FakeCoordinator({"P": make_point("")})
    assert _sensor(coord).native_value is None


def test_native_value_decodes_enum_via_format_texts():
    coord = FakeCoordinator({"P": make_point("2", format_texts="Aus|Auto|Ein")})
    assert _sensor(coord).native_value == "Ein"


def test_native_value_enum_out_of_range_falls_back_to_raw_value():
    coord = FakeCoordinator({"P": make_point("9", format_texts="Aus|Auto|Ein")})
    assert _sensor(coord).native_value == "9"


def test_native_value_applies_divisor_and_rounds():
    coord = FakeCoordinator({"P": make_point("235", divisor="10")})
    assert _sensor(coord).native_value == 23.5


def test_native_value_divisor_result_returned_as_int_when_whole():
    coord = FakeCoordinator({"P": make_point("200", divisor="10")})
    value = _sensor(coord).native_value
    assert value == 20
    assert isinstance(value, int)


def test_native_value_temperature_device_class_converts_to_float():
    config = {"parameter": "P", "name": "N", "device_class": SensorDeviceClass.TEMPERATURE}
    coord = FakeCoordinator({"P": make_point("21")})
    assert _sensor(coord, config).native_value == 21.0


def test_native_value_numeric_string_without_divisor_becomes_int():
    coord = FakeCoordinator({"P": make_point("42")})
    value = _sensor(coord).native_value
    assert value == 42
    assert isinstance(value, int)


def test_native_value_non_numeric_text_returned_as_is():
    """The device occasionally reports a text status (e.g. "leer" for an
    absent/uncalibrated pellet-level sensor) instead of a number."""
    coord = FakeCoordinator({"P": make_point("leer")})
    assert _sensor(coord).native_value == "leer"


# --- native_unit_of_measurement --------------------------------------------

def test_native_unit_suppressed_for_non_numeric_value():
    coord = FakeCoordinator({"P": make_point("leer")})
    assert _sensor(coord).native_unit_of_measurement is None


def test_native_unit_maps_device_unit_text_to_ha_unit():
    point = make_point("21")
    point["unitText"] = "°C"
    coord = FakeCoordinator({"P": point})
    assert _sensor(coord).native_unit_of_measurement == UnitOfTemperature.CELSIUS


def test_native_unit_maps_percent_symbol():
    point = make_point("50")
    point["unitText"] = "%"
    coord = FakeCoordinator({"P": point})
    assert _sensor(coord).native_unit_of_measurement == PERCENTAGE


def test_native_unit_falls_back_to_configured_unit_when_device_omits_it():
    config = {"parameter": "P", "name": "N", "unit": "EH"}
    coord = FakeCoordinator({"P": make_point("42")})
    assert _sensor(coord, config).native_unit_of_measurement == "EH"


# --- state_class / device_class suppression on non-numeric values ---------

def test_state_class_present_when_configured_and_numeric():
    config = {"parameter": "P", "name": "N", "state_class": SensorStateClass.MEASUREMENT}
    coord = FakeCoordinator({"P": make_point("21")})
    assert _sensor(coord, config).state_class == SensorStateClass.MEASUREMENT


def test_state_class_suppressed_when_value_non_numeric():
    config = {"parameter": "P", "name": "N", "state_class": SensorStateClass.MEASUREMENT}
    coord = FakeCoordinator({"P": make_point("leer")})
    assert _sensor(coord, config).state_class is None


def test_device_class_suppressed_when_value_non_numeric():
    config = {"parameter": "P", "name": "N", "device_class": SensorDeviceClass.TEMPERATURE}
    coord = FakeCoordinator({"P": make_point("leer")})
    assert _sensor(coord, config).device_class is None


def test_device_class_none_when_not_configured():
    coord = FakeCoordinator({"P": make_point("21")})
    assert _sensor(coord).device_class is None


# --- available --------------------------------------------------------------

def test_available_false_when_coordinator_update_failed():
    coord = FakeCoordinator({"P": make_point("1")}, last_update_success=False)
    assert _sensor(coord).available is False


def test_available_false_when_parameter_missing():
    coord = FakeCoordinator({})
    assert _sensor(coord).available is False


def test_available_false_when_status_not_ok():
    coord = FakeCoordinator({"P": make_point("1", status="ERROR")})
    assert _sensor(coord).available is False


def test_available_true_when_status_ok():
    coord = FakeCoordinator({"P": make_point("1", status="OK")})
    assert _sensor(coord).available is True


# --- name -------------------------------------------------------------------

def test_name_uses_device_short_text_when_present():
    point = make_point("1")
    point["shortText"] = "Kesseltemperatur"
    coord = FakeCoordinator({"P": point})
    assert _sensor(coord).name == "Kesseltemperatur"


def test_name_falls_back_to_configured_name_when_short_text_blank():
    coord = FakeCoordinator({"P": make_point("1")})
    assert _sensor(coord).name == "N"


# --- extra_state_attributes -------------------------------------------------

def test_extra_state_attributes_empty_when_parameter_missing():
    assert _sensor(FakeCoordinator({})).extra_state_attributes == {}


def test_extra_state_attributes_includes_raw_value_divisor_and_limits():
    point = make_point("235", divisor="10", lower_limit="0", upper_limit="900")
    point["unitText"] = "°C"
    coord = FakeCoordinator({"P": point})
    attrs = _sensor(coord).extra_state_attributes

    assert attrs["parameter"] == "P"
    assert attrs["status"] == "OK"
    assert attrs["raw_value"] == "235"
    assert attrs["divisor"] == "10"
    assert attrs["unit_from_device"] == "°C"
    assert attrs["lower_limit"] == "0"
    assert attrs["upper_limit"] == "900"
