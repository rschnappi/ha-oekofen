"""Tests for the Störmelderelais (fault relay) notification watcher in sensor.py."""
from unittest.mock import MagicMock, patch

from custom_components.oekofen.sensor import (
    FAULT_RELAY_PARAMETER,
    _is_relay_active,
    _register_fault_relay_watcher,
)

from .conftest import make_point


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


def test_watcher_does_not_repeat_notification_while_still_active():
    coord = ListenerCoordinator({FAULT_RELAY_PARAMETER: make_point("1")})
    hass = MagicMock()

    with patch("custom_components.oekofen.sensor.persistent_notification") as mock_pn:
        _register_fault_relay_watcher(hass, coord, "entry1")
        assert mock_pn.async_create.call_count == 1

        coord.fire()
        coord.fire()

        assert mock_pn.async_create.call_count == 1
