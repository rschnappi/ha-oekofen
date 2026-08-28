"""Tests for the Kesselstatus-phase-duration diagnostics (Zündzeit, Saugdauer -
ignition_diagnostics.py)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.number import RestoreNumber
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.oekofen.ignition_diagnostics import (
    DEFAULT_WARNSCHWELLE_MINUTES,
    KESSELSTATUS_PARAMETER,
    OekofenGluehstabWarnschwelle,
    OekofenGluehstabZuendzeit,
    OekofenNachlaufdauer,
    OekofenSaugdauer,
    OekofenSoftstartdauer,
    _is_zuendung,
    _label_matches,
    _resolve_label,
    _PhaseDurationExtraStoredData,
    get_warnschwelle,
)

from .conftest import FakeCoordinator, make_point

FORMAT_TEXTS = "Aus|Start|Zuendung|Softstart|Leistungsbrand|Saugen|Nachlauf"


def _point(label: str):
    index = FORMAT_TEXTS.split("|").index(label)
    return make_point(str(index), format_texts=FORMAT_TEXTS)


def test_resolve_label_uses_format_texts_index():
    assert _resolve_label(_point("Zuendung")) == "Zuendung"
    assert _resolve_label(_point("Softstart")) == "Softstart"


def test_resolve_label_none_when_missing_or_blank():
    assert _resolve_label(None) is None
    assert _resolve_label(make_point("")) is None


def test_resolve_label_out_of_range_returns_raw_value():
    # Mirrors OekofenSensor.native_value: falls back to the raw value
    # rather than hiding it, but that raw value can never match "zuendung".
    label = _resolve_label(make_point("99", format_texts=FORMAT_TEXTS))
    assert label == "99"
    assert _is_zuendung(label) is False


def test_is_zuendung_case_and_whitespace_insensitive():
    assert _is_zuendung("Zuendung") is True
    assert _is_zuendung(" zuendung ") is True
    assert _is_zuendung("Softstart") is False
    assert _is_zuendung(None) is None


def test_label_matches_is_generic_over_target():
    assert _label_matches("Saugen", "saugen") is True
    assert _label_matches(" Saugen ", "saugen") is True
    assert _label_matches("Zuendung", "saugen") is False
    assert _label_matches(None, "saugen") is None


def test_get_warnschwelle_default_when_entity_missing():
    hass = MagicMock()
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = None
        assert get_warnschwelle(hass, "entry1") == DEFAULT_WARNSCHWELLE_MINUTES


def test_get_warnschwelle_reads_current_entity_state():
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="480")
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = "number.x_gluehstab_warnschwelle"
        assert get_warnschwelle(hass, "entry1") == 480.0


def test_get_warnschwelle_falls_back_on_unavailable_state():
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="unavailable")
    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        mock_er.return_value.async_get_entity_id.return_value = "number.x_gluehstab_warnschwelle"
        assert get_warnschwelle(hass, "entry1") == DEFAULT_WARNSCHWELLE_MINUTES


def _make_entity(coordinator, cls=OekofenGluehstabZuendzeit):
    entity = cls(coordinator, "entry1", "Test")
    entity.hass = MagicMock()
    entity.async_write_ha_state = MagicMock()
    return entity


def test_extra_stored_data_round_trip_preserves_in_progress_phase():
    since = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    data = _PhaseDurationExtraStoredData(native_value=408, phase_since=since, last_in_phase=True)

    restored = _PhaseDurationExtraStoredData.from_dict(data.as_dict())

    assert restored.native_value == 408
    assert restored.phase_since == since
    assert restored.last_in_phase is True


def test_extra_stored_data_round_trip_handles_no_in_progress_phase():
    data = _PhaseDurationExtraStoredData(native_value=408, phase_since=None, last_in_phase=False)
    restored = _PhaseDurationExtraStoredData.from_dict(data.as_dict())
    assert restored.phase_since is None
    assert restored.last_in_phase is False


def test_extra_restore_state_data_reflects_current_tracking_state():
    entity = _make_entity(FakeCoordinator({}))
    since = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    entity._phase_since = since
    entity._last_in_phase = True
    entity._attr_native_value = None

    stored = entity.extra_restore_state_data

    assert stored.phase_since == since
    assert stored.last_in_phase is True


async def test_async_added_to_hass_restores_in_progress_phase_across_restart():
    """A restart landing mid-occurrence must not lose track of when it
    started - otherwise that occurrence's duration is silently never
    recorded once it later completes."""
    entity = _make_entity(FakeCoordinator({}))
    since = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    stored = _PhaseDurationExtraStoredData(native_value=6.8, phase_since=since, last_in_phase=True)

    with patch.object(CoordinatorEntity, "async_added_to_hass", AsyncMock()):
        entity.async_get_last_extra_data = AsyncMock(
            return_value=MagicMock(as_dict=MagicMock(return_value=stored.as_dict()))
        )
        await entity.async_added_to_hass()

    assert entity._attr_native_value == 6.8
    assert entity._phase_since == since
    assert entity._last_in_phase is True


def test_migrates_away_from_stale_seconds_unit_override():
    """See _async_migrate_unit_override's docstring: HA's own SensorEntity
    silently pins a duration sensor to its original unit the first time the
    native unit changes, to protect existing statistics - undo that pin
    once minutes is the sensor's real native unit. Live-reproduced: a
    native 8.2 min value kept displaying as "492 s" until this ran."""
    entity = _make_entity(FakeCoordinator({}))
    entity.entity_id = "sensor.test_gluehstab_zundzeit"
    entity.registry_entry = MagicMock(options={"sensor.private": {"suggested_unit_of_measurement": "s"}})

    new_entry = MagicMock(options={})
    mock_registry = MagicMock()
    mock_registry.async_update_entity_options.return_value = new_entry

    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get", return_value=mock_registry):
        with patch.object(OekofenGluehstabZuendzeit, "_async_read_entity_options", MagicMock()) as mock_read:
            entity._async_migrate_unit_override()

    mock_registry.async_update_entity_options.assert_called_once_with(
        "sensor.test_gluehstab_zundzeit", "sensor.private", None
    )
    assert entity.registry_entry is new_entry
    mock_read.assert_called_once()


def test_unit_migration_noop_when_no_override_present():
    entity = _make_entity(FakeCoordinator({}))
    entity.registry_entry = MagicMock(options={})

    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        entity._async_migrate_unit_override()

    mock_er.assert_not_called()


def test_unit_migration_noop_when_override_already_matches_native_unit():
    entity = _make_entity(FakeCoordinator({}))
    entity.registry_entry = MagicMock(
        options={"sensor.private": {"suggested_unit_of_measurement": "min"}}
    )

    with patch("custom_components.oekofen.ignition_diagnostics.er.async_get") as mock_er:
        entity._async_migrate_unit_override()

    mock_er.assert_not_called()


def test_no_value_yet_leaves_state_unset():
    coord = FakeCoordinator({})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()
    assert entity._attr_native_value is None


def test_first_seen_value_does_not_trigger_transition():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Zuendung")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()
    assert entity._phase_since is None  # no prior state to compare against yet
    assert entity._last_in_phase is True


def test_warm_restart_skipping_zuendung_never_starts_a_timer():
    """Kesselstatus can go Saugen -> Leistungsbrand directly (embers still hot);
    without ever passing through "Zuendung" the sensor must stay unset."""
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Saugen")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Leistungsbrand")
    entity._handle_coordinator_update()

    assert entity._attr_native_value is None
    assert entity._phase_since is None


def test_zuendung_to_softstart_records_duration_and_checks_threshold():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Start")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()  # baseline: not zuendung

    coord.data[KESSELSTATUS_PARAMETER] = _point("Zuendung")
    entity._handle_coordinator_update()  # -> Zuendung
    assert entity._phase_since is not None

    with patch("custom_components.oekofen.ignition_diagnostics.get_warnschwelle", return_value=999):
        with patch("custom_components.oekofen.ignition_diagnostics.async_create_notification") as mock_notify:
            coord.data[KESSELSTATUS_PARAMETER] = _point("Softstart")
            entity._handle_coordinator_update()  # Zuendung -> Softstart

            assert entity._phase_since is None
            assert entity._attr_native_value is not None
            assert entity._attr_native_value >= 0
            mock_notify.assert_not_called()  # under threshold


def test_duration_over_threshold_triggers_notification():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Start")})
    entity = _make_entity(coord)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Zuendung")
    entity._handle_coordinator_update()

    with patch("custom_components.oekofen.ignition_diagnostics.get_warnschwelle", return_value=-1):
        with patch("custom_components.oekofen.ignition_diagnostics.async_create_notification") as mock_notify:
            coord.data[KESSELSTATUS_PARAMETER] = _point("Softstart")
            entity._handle_coordinator_update()

            mock_notify.assert_called_once()
            _, kwargs = mock_notify.call_args
            assert kwargs["notification_id"] == "oekofen_gluehstab_warnung_entry1"


def test_warnschwelle_defaults_and_bounds():
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    assert entity._attr_native_value == DEFAULT_WARNSCHWELLE_MINUTES
    assert entity._attr_native_min_value == 1
    assert entity._attr_native_max_value == 15
    assert entity.unique_id == "entry1_gluehstab_warnschwelle"


async def test_warnschwelle_set_native_value():
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    entity.async_write_ha_state = MagicMock()
    await entity.async_set_native_value(7.5)
    assert entity._attr_native_value == 7.5
    entity.async_write_ha_state.assert_called_once()


async def test_warnschwelle_restores_legacy_seconds_value_as_minutes():
    """A value restored from before this entity switched from seconds to
    minutes (e.g. the old 600s default) must be converted, not restored
    as-is - "600 min" would be wildly out of the new 1-15 bounds."""
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    entity.async_get_last_number_data = AsyncMock(return_value=MagicMock(native_value=600))

    with patch.object(RestoreNumber, "async_added_to_hass", AsyncMock()):
        await entity.async_added_to_hass()

    assert entity._attr_native_value == 10.0


async def test_warnschwelle_restores_plausible_minutes_value_unchanged():
    entity = OekofenGluehstabWarnschwelle("entry1", "Test")
    entity.async_get_last_number_data = AsyncMock(return_value=MagicMock(native_value=7.5))

    with patch.object(RestoreNumber, "async_added_to_hass", AsyncMock()):
        await entity.async_added_to_hass()

    assert entity._attr_native_value == 7.5


async def test_zuendzeit_restores_legacy_seconds_value_as_minutes():
    entity = _make_entity(FakeCoordinator({}))
    stored = _PhaseDurationExtraStoredData(native_value=408, phase_since=None, last_in_phase=False)

    with patch.object(CoordinatorEntity, "async_added_to_hass", AsyncMock()):
        entity.async_get_last_extra_data = AsyncMock(
            return_value=MagicMock(as_dict=MagicMock(return_value=stored.as_dict()))
        )
        await entity.async_added_to_hass()

    assert entity._attr_native_value == 6.8


# --- OekofenSaugdauer -------------------------------------------------------
# Same _KesselstatusPhaseDuration base as Zündzeit above (restore, unit
# migration, transition-detection are already covered there) - these only
# check what's specific to this subclass: which label it tracks, its
# key/name, and that it does *not* fire a warning notification (that's
# Zündzeit-only behaviour, tied to glow-plug wear, not suction duration).

def test_saugdauer_unique_id_and_name():
    entity = _make_entity(FakeCoordinator({}), cls=OekofenSaugdauer)
    assert entity.unique_id == "entry1_saugdauer"
    assert entity._attr_name == "Saugdauer"


def test_saugdauer_tracks_saugen_not_zuendung():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Start")})
    entity = _make_entity(coord, cls=OekofenSaugdauer)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Zuendung")
    entity._handle_coordinator_update()
    assert entity._phase_since is None  # ignition isn't this sensor's phase

    coord.data[KESSELSTATUS_PARAMETER] = _point("Saugen")
    entity._handle_coordinator_update()
    assert entity._phase_since is not None


def test_saugdauer_records_duration_without_notification():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Nachlauf")})
    entity = _make_entity(coord, cls=OekofenSaugdauer)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Saugen")
    entity._handle_coordinator_update()

    with patch("custom_components.oekofen.ignition_diagnostics.async_create_notification") as mock_notify:
        coord.data[KESSELSTATUS_PARAMETER] = _point("Start")
        entity._handle_coordinator_update()

        assert entity._phase_since is None
        assert entity._attr_native_value is not None
        assert entity._attr_native_value >= 0
        mock_notify.assert_not_called()


# --- OekofenSoftstartdauer / OekofenNachlaufdauer ---------------------------
# Same _KesselstatusPhaseDuration base as Zündzeit/Saugdauer above - only
# check what's specific to each subclass (label tracked, key/name).

def test_softstartdauer_unique_id_and_name():
    entity = _make_entity(FakeCoordinator({}), cls=OekofenSoftstartdauer)
    assert entity.unique_id == "entry1_softstartdauer"
    assert entity._attr_name == "Softstartdauer"


def test_softstartdauer_tracks_softstart_and_records_duration():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Zuendung")})
    entity = _make_entity(coord, cls=OekofenSoftstartdauer)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Softstart")
    entity._handle_coordinator_update()
    assert entity._phase_since is not None

    coord.data[KESSELSTATUS_PARAMETER] = _point("Leistungsbrand")
    entity._handle_coordinator_update()

    assert entity._phase_since is None
    assert entity._attr_native_value is not None
    assert entity._attr_native_value >= 0


def test_nachlaufdauer_unique_id_and_name():
    entity = _make_entity(FakeCoordinator({}), cls=OekofenNachlaufdauer)
    assert entity.unique_id == "entry1_nachlaufdauer"
    assert entity._attr_name == "Nachlaufdauer"


def test_nachlaufdauer_tracks_nachlauf_and_records_duration():
    coord = FakeCoordinator({KESSELSTATUS_PARAMETER: _point("Leistungsbrand")})
    entity = _make_entity(coord, cls=OekofenNachlaufdauer)
    entity._handle_coordinator_update()

    coord.data[KESSELSTATUS_PARAMETER] = _point("Nachlauf")
    entity._handle_coordinator_update()
    assert entity._phase_since is not None

    coord.data[KESSELSTATUS_PARAMETER] = _point("Aus")
    entity._handle_coordinator_update()

    assert entity._phase_since is None
    assert entity._attr_native_value is not None
    assert entity._attr_native_value >= 0
