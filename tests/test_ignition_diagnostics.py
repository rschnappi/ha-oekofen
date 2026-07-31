"""Tests for the Glühstab ignition-duration diagnostics (ignition_diagnostics.py)."""
from unittest.mock import MagicMock, patch

from custom_components.oekofen.ignition_diagnostics import (
    DEFAULT_WARNSCHWELLE_SECONDS,
    GLUEHSTAB_PARAMETER,
    OekofenGluehstabWarnschwelle,
    OekofenGluehstabZuendzeit,
    _is_off,
    get_warnschwelle,
)

from .conftest import FakeCoordinator, make_point


def test_is_off_handles_whitespace_and_case():
    assert _is_off(" Aus") is True
    assert _is_off("aus") is True
    assert _is_off("AUS") is True
    assert _is_off("Ein") is False
    assert _is_off("") is None
    assert _is_off(None) is None


def test_get_warnschwelle_default_when_entity_missing():
    hass = MagicMock()
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = None
        assert get_warnschwelle(hass, "entry1") == DEFAULT_WARNSCHWELLE_SECONDS


def test_get_warnschwelle_reads_current_entity_state():
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="180")
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = "number.x_gluehstab_warnschwelle"
        assert get_warnschwelle(hass, "entry1") == 180.0


def test_get_warnschwelle_falls_back_on_unavailable_state():
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="unavailable")
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = "number.x_gluehstab_warnschwelle"
        assert get_warnschwelle(hass, "entry1") == DEFAULT_WARNSCHWELLE_SECONDS


def _make_entity(coordinator):
    entity = OekofenGluehstabZuendzeit(coordinator, "entry1", "Test")
    entity.hass = MagicMock()
    entity.async_write_ha_state = MagicMock()
    return entity


def test_no_value_yet_leaves_state_unset():
    coord = FakeCoordinator({})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()
    assert entity._attr_native_value is None


def test_first_seen_value_does_not_trigger_transition():
    coord = FakeCoordinator({GLUEHSTAB_PARAMETER: make_point("Ein")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()
    assert entity._on_since is None  # no prior state to compare against yet
    assert entity._last_state_off is False


def test_off_to_on_to_off_records_duration_and_checks_threshold():
    coord = FakeCoordinator({GLUEHSTAB_PARAMETER: make_point("Aus")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()  # establishes baseline: off

    coord.data[GLUEHSTAB_PARAMETER] = make_point("Ein")
    entity._handle_coordinator_update()  # off -> on
    assert entity._on_since is not None

    with patch("custom_components.oekofen.ignition_diagnostics.get_warnschwelle", return_value=999):
        with patch("custom_components.oekofen.ignition_diagnostics.async_create_notification") as mock_notify:
            coord.data[GLUEHSTAB_PARAMETER] = make_point("Aus")
            entity._handle_coordinator_update()  # on -> off

            assert entity._on_since is None
            assert entity._attr_native_value is not None
            assert entity._attr_native_value >= 0
            mock_notify.assert_not_called()  # under threshold


def test_duration_over_threshold_triggers_notification():
    coord = FakeCoordinator({GLUEHSTAB_PARAMETER: make_point("Aus")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()

    coord.data[GLUEHSTAB_PARAMETER] = make_point("Ein")
    entity._handle_coordinator_update()

    with patch("custom_components.oekofen.ignition_diagnostics.get_warnschwelle", return_value=-1):
        with patch("custom_components.oekofen.ignition_diagnostics.async_create_notification") as mock_notify:
            coord.data[GLUEHSTAB_PARAMETER] = make_point("Aus")
            entity._handle_coordinator_update()

            mock_notify.assert_called_once()
            _, kwargs = mock_notify.call_args
            assert kwargs["notification_id"] == "oekofen_gluehstab_warnung_entry1"


def test_warnschwelle_defaults_and_bounds():
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    assert entity._attr_native_value == DEFAULT_WARNSCHWELLE_SECONDS
    assert entity._attr_native_min_value == 30
    assert entity._attr_native_max_value == 900
    assert entity.unique_id == "entry1_gluehstab_warnschwelle"


async def test_warnschwelle_set_native_value():
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    entity.async_write_ha_state = MagicMock()
    await entity.async_set_native_value(300)
    assert entity._attr_native_value == 300
    entity.async_write_ha_state.assert_called_once()
