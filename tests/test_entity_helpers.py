"""Direct tests for entity_helpers.py (build_device_info/parameter_available),
shared across 8+ platform files - see the module docstring."""
from custom_components.oekofen.entity_helpers import build_device_info, parameter_available

from .conftest import FakeCoordinator


def test_build_device_info_shape():
    info = build_device_info("entry1", "Test Device")
    assert info == {
        "identifiers": {("oekofen", "entry1")},
        "name": "Test Device",
        "manufacturer": "ÖkOfen",
        "model": "Pellematic",
    }


def test_parameter_available_true_when_present_and_healthy():
    coord = FakeCoordinator({"P": {"value": "1"}})
    assert parameter_available(coord, "P") is True


def test_parameter_available_false_when_parameter_missing():
    coord = FakeCoordinator({})
    assert parameter_available(coord, "P") is False


def test_parameter_available_false_when_last_update_failed():
    coord = FakeCoordinator({"P": {"value": "1"}}, last_update_success=False)
    assert parameter_available(coord, "P") is False
