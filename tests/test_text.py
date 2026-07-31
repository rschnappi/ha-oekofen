"""Tests for the text platform (text.py) - Fernwartung/Mail settings."""
from unittest.mock import AsyncMock

from homeassistant.components.text import TextMode

from custom_components.oekofen.text import (
    MAIL_EMPFAENGER_COUNT,
    OekofenText,
    build_text_definitions,
)

from .conftest import FakeCoordinator, make_point


def test_build_text_definitions_has_expected_keys():
    defs = build_text_definitions()
    assert defs["mail_anlagenbezeichnung"]["parameter"] == "CAPPL:LOCAL.fernwartung_anlagenbezeichung"
    assert defs["mail_postausgangsserver"]["parameter"] == "CAPPL:LOCAL.fernwartung_mail_postausgangsserver"
    assert defs["mail_benutzer"]["parameter"] == "CAPPL:LOCAL.fernwartung_mail_benutzer"
    assert defs["mail_passwort"]["parameter"] == "CAPPL:LOCAL.fernwartung_mail_passwort"
    assert defs["mail_passwort"]["mode"] == TextMode.PASSWORD
    assert len([k for k in defs if k.startswith("mail_empfaenger_")]) == MAIL_EMPFAENGER_COUNT
    assert defs["mail_empfaenger_0"]["parameter"] == "CAPPL:LOCAL.fernwartung_mail_empfaenger[0]"
    assert defs["mail_empfaenger_4"]["parameter"] == "CAPPL:LOCAL.fernwartung_mail_empfaenger[4]"


def _make_entity(coordinator, config=None, api=None):
    config = config or build_text_definitions()["mail_benutzer"]
    return OekofenText(coordinator, api or AsyncMock(), "mail_benutzer", config, entry_id="e1", device_name="Test")


def test_native_value_reads_from_coordinator():
    config = build_text_definitions()["mail_benutzer"]
    coord = FakeCoordinator({config["parameter"]: make_point("smtp-user")})
    entity = _make_entity(coord, config)
    assert entity.native_value == "smtp-user"


def test_native_value_none_when_missing():
    config = build_text_definitions()["mail_benutzer"]
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.native_value is None


def test_mode_defaults_to_text_and_password_field_uses_password_mode():
    defs = build_text_definitions()
    assert _make_entity(FakeCoordinator({}), defs["mail_benutzer"])._attr_mode == TextMode.TEXT
    assert _make_entity(FakeCoordinator({}), defs["mail_passwort"])._attr_mode == TextMode.PASSWORD


async def test_async_set_value_writes_raw_string():
    config = build_text_definitions()["mail_postausgangsserver"]
    api = AsyncMock()
    coord = FakeCoordinator({config["parameter"]: make_point("")})
    entity = _make_entity(coord, config, api=api)

    await entity.async_set_value("smtp.example.com")

    api.set_data.assert_awaited_once_with(config["parameter"], "smtp.example.com")
    assert coord.refresh_calls == 1


def test_available_false_when_parameter_missing():
    config = build_text_definitions()["mail_benutzer"]
    entity = _make_entity(FakeCoordinator({}), config)
    assert entity.available is False
