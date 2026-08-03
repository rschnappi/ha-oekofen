"""Tests for the Anlage-Betriebsart slot resolution helpers (betriebsart.py)."""
from custom_components.oekofen.betriebsart import (
    ANLAGE_MODE_PARAMETER,
    active_betriebsart_slot,
    betriebsart_parameter,
    betriebsart_slot_parameters,
)

from .conftest import make_point


def test_active_slot_defaults_to_zero_when_missing():
    assert active_betriebsart_slot({}) == 0


def test_active_slot_defaults_to_zero_when_blank():
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("")}) == 0


def test_active_slot_reads_current_anlage_mode():
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("0")}) == 0
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("1")}) == 1
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("2")}) == 2


def test_active_slot_falls_back_to_zero_for_out_of_range_or_invalid():
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("99")}) == 0
    assert active_betriebsart_slot({ANLAGE_MODE_PARAMETER: make_point("not-a-number")}) == 0


def test_betriebsart_parameter_builds_slot_string():
    data = {ANLAGE_MODE_PARAMETER: make_point("1")}
    assert betriebsart_parameter("CAPPL:LOCAL.hk[0]", data) == "CAPPL:LOCAL.hk[0].betriebsart[1]"


def test_betriebsart_slot_parameters_lists_all_three():
    assert betriebsart_slot_parameters("CAPPL:LOCAL.ww[0]") == [
        "CAPPL:LOCAL.ww[0].betriebsart[0]",
        "CAPPL:LOCAL.ww[0].betriebsart[1]",
        "CAPPL:LOCAL.ww[0].betriebsart[2]",
    ]
