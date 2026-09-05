"""Tests for dashboard.py - the Python port of the old oekofen-strategy.js
dashboard-strategy view-building logic (see dashboard.py's module docstring
for why it moved server-side)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.oekofen.dashboard import (
    DASHBOARD_URL_PATH,
    Circuit,
    analyze_entities,
    async_build_wartung_view,
    async_regenerate_dashboard,
    build_circuit_view,
    build_overview_views,
    build_puffer_pumpen_view,
    build_settings_grid,
    build_statistik_view,
    common_prefix,
    domain_of,
    object_id_of,
)


def fake_state(state, **attributes):
    return SimpleNamespace(state=state, attributes=attributes)


def test_domain_and_object_id_of():
    assert domain_of("sensor.heizraum_ofen_kesseltemperatur") == "sensor"
    assert object_id_of("sensor.heizraum_ofen_kesseltemperatur") == "heizraum_ofen_kesseltemperatur"


def test_common_prefix_trims_back_to_last_underscore():
    ids = ["heizraum_ofen_heizkreis_1_betriebsart", "heizraum_ofen_heizkreis_1_temperatur"]
    assert common_prefix(ids) == "heizraum_ofen_heizkreis_1_"


def test_common_prefix_stops_at_first_divergent_underscore_group():
    ids = ["heizraum_ofen_kesseltemperatur", "heizraum_ofen_aussentemperatur"]
    assert common_prefix(ids) == "heizraum_ofen_"


def test_common_prefix_empty_for_no_ids():
    assert common_prefix([]) == ""


def test_analyze_entities_groups_circuit_entities_by_relative_suffix():
    entity_ids = [
        "select.heizraum_ofen_heizkreis_1_betriebsart",
        "sensor.heizraum_ofen_heizkreis_1_temperatur",
        "climate.heizraum_ofen_heizkreis_1",
        "sensor.heizraum_ofen_kesseltemperatur",
    ]

    result = analyze_entities(entity_ids)

    assert result.prefix == "heizraum_ofen_"
    assert len(result.circuits) == 1
    circuit = result.circuits[0]
    assert circuit.type == "heizkreis"
    assert circuit.index == 1
    assert circuit.entity("select", "betriebsart") == "select.heizraum_ofen_heizkreis_1_betriebsart"
    assert circuit.entity("sensor", "temperatur") == "sensor.heizraum_ofen_heizkreis_1_temperatur"
    # The climate entity's own suffix *is* the circuit suffix (no trailing
    # "_something"), so its "relative" key is the empty string.
    assert circuit.entity("climate", "") == "climate.heizraum_ofen_heizkreis_1"
    assert result.leftover == ["sensor.heizraum_ofen_kesseltemperatur"]


def test_analyze_entities_orders_circuits_by_type_then_index():
    entity_ids = [
        "sensor.x_warmwasser_1_a",
        "sensor.x_heizkreis_2_a",
        "sensor.x_heizkreis_1_a",
    ]

    result = analyze_entities(entity_ids)

    assert [(c.type, c.index) for c in result.circuits] == [
        ("heizkreis", 1),
        ("heizkreis", 2),
        ("warmwasser", 1),
    ]


def test_build_settings_grid_splits_installer_warned_entities():
    circuit = Circuit(type="heizkreis", index=1, suffix="heizkreis_1")
    circuit.entities["number:normal_feld"] = "number.x_heizkreis_1_normal_feld"
    circuit.entities["number:installateur_feld"] = "number.x_heizkreis_1_installateur_feld"
    states = {
        "number.x_heizkreis_1_normal_feld": fake_state("5"),
        "number.x_heizkreis_1_installateur_feld": fake_state("2", warnhinweis="Nur vom Installateur ändern!"),
    }

    cards, warned_ids, warning_text = build_settings_grid(circuit, [], states)

    assert [c["entity"] for c in cards] == ["number.x_heizkreis_1_normal_feld"]
    assert warned_ids == ["number.x_heizkreis_1_installateur_feld"]
    assert warning_text == "Nur vom Installateur ändern!"


def test_build_settings_grid_excludes_zeitprogramm_entities():
    circuit = Circuit(type="heizkreis", index=1, suffix="heizkreis_1")
    circuit.entities["select:zeit_1_montag_aktiv"] = "select.x_heizkreis_1_zeit_1_montag_aktiv"
    states = {"select.x_heizkreis_1_zeit_1_montag_aktiv": fake_state("on")}

    cards, warned_ids, _ = build_settings_grid(circuit, [], states)

    assert cards == []
    assert warned_ids == []


def test_build_circuit_view_does_not_duplicate_installer_only_extra_fields():
    """Regression test: Vorrang/Legionellenschutz (in the Party/Urlaub extra-
    field list) must not also show up in the generic Einstellungen grid -
    that duplication was a real, previously-shipped bug (see git history),
    caused by reserving the extra fields via used_for_settings only *after*
    build_settings_grid had already scanned for unclaimed entities."""
    circuit = Circuit(type="heizkreis", index=1, suffix="heizkreis_1")
    circuit.entities["select:vorrang"] = "select.x_heizkreis_1_vorrang"
    states = {"select.x_heizkreis_1_vorrang": fake_state("aus", warnhinweis="Nur vom Installateur ändern!")}

    view = build_circuit_view(circuit, states)

    rendered = str(view)
    assert rendered.count("select.x_heizkreis_1_vorrang") == 1


def test_build_overview_views_splits_diagnose_and_mail_smtp():
    circuits = []
    leftover = [
        "sensor.x_diag_1",
        "text.x_smtp_server",
    ]
    states = {}

    views = build_overview_views(circuits, leftover, states)

    titles = [v["title"] for v in views]
    assert titles == ["Übersicht", "Diagnose", "Mail / SMTP"]


def test_build_overview_views_surfaces_button_entities():
    """Regression test: button.py's device-clock sync button (and any
    future button entity) is a leftover entity like datetime/select/switch/
    number - it must show up in the Übersicht, not silently disappear
    because "button" was missing from _DOMAIN_TITLES."""
    circuits = []
    leftover = ["button.x_gerateuhrzeit_synchronisieren"]
    states = {}

    views = build_overview_views(circuits, leftover, states)

    rendered = str(views[0])
    assert "button.x_gerateuhrzeit_synchronisieren" in rendered


def test_build_statistik_view_splits_feuerraum_from_normal_temperatures():
    entity_ids = ["sensor.x_kesseltemperatur", "sensor.x_feuerraumtemperatur"]
    states = {
        "sensor.x_kesseltemperatur": fake_state("60", device_class="temperature"),
        "sensor.x_feuerraumtemperatur": fake_state("400", device_class="temperature"),
    }

    view = build_statistik_view(entity_ids, states)

    history_titles = [c["title"] for c in view["cards"] if c.get("type") == "history-graph"]
    assert "Temperaturverlauf" in history_titles
    assert "Feuerraumtemperatur" in history_titles


def test_build_statistik_view_returns_none_when_nothing_to_show():
    assert build_statistik_view(["sensor.x_text_only"], {"sensor.x_text_only": fake_state("hello")}) is None


def test_build_puffer_pumpen_view_labels_known_suffixes():
    view = build_puffer_pumpen_view(["sensor.x_buffer_top_temperature"], "x_")

    tile = view["cards"][0]["cards"][1]["cards"][0]
    assert tile["name"] == "Puffer Oben Ist"


async def test_async_build_wartung_view_returns_none_without_matching_calendar():
    hass = MagicMock()
    hass.states.async_all.return_value = []

    assert await async_build_wartung_view(hass) is None


async def test_async_build_wartung_view_lists_next_three_events():
    hass = MagicMock()
    calendar_state = fake_state("on", friendly_name="Ofen Wartung")
    calendar_state.entity_id = "calendar.ofen_wartung"
    hass.states.async_all.return_value = [calendar_state]
    hass.states.get.return_value = calendar_state
    hass.services.async_call = AsyncMock(
        return_value={
            "calendar.ofen_wartung": {
                "events": [
                    {"summary": "Rauchfangkehrer", "start": "2026-11-05T09:00:00+00:00"},
                    {"summary": "Service Ofen", "start": "2026-10-01T09:00:00+00:00"},
                ]
            }
        }
    )

    view = await async_build_wartung_view(hass)

    assert view["title"] == "Wartung"
    assert view["cards"][1]["entities"] == ["calendar.ofen_wartung"]
    assert "Service Ofen" in view["cards"][0]["content"]
    assert view["cards"][0]["content"].index("Service Ofen") < view["cards"][0]["content"].index("Rauchfangkehrer")


async def test_async_build_wartung_view_shows_automatic_shutdown_info():
    """When a "ÖkOfen: Anlage vor Wartungstermin ausschalten" blueprint
    automation is configured, the Wartung view must also show: the
    automation's own on/off state, the switched select entity, a restore
    button for the saved scene, and an info card with the check time,
    keywords and notify target - all read live from that automation's own
    configured blueprint inputs, not a generic explanation."""
    from homeassistant.components.automation import DATA_COMPONENT as AUTOMATION_DATA_COMPONENT

    hass = MagicMock()
    calendar_state = fake_state("on", friendly_name="Ofen Wartung")
    calendar_state.entity_id = "calendar.ofen_wartung"
    scene_state = fake_state("2026-09-05T20:00:00+00:00")
    hass.states.async_all.return_value = [calendar_state]
    hass.states.get.side_effect = lambda eid: {
        "calendar.ofen_wartung": calendar_state,
        "scene.oekofen_zustand_vor_wartung": scene_state,
    }.get(eid)
    hass.services.async_call = AsyncMock(return_value={"calendar.ofen_wartung": {"events": []}})

    automation_entity = MagicMock()
    automation_entity.entity_id = "automation.oekofen_wartung_vorbereiten"
    automation_entity.referenced_blueprint = "oekofen/wartung_vorbereiten.yaml"
    automation_entity._blueprint_inputs = {
        "use_blueprint": {
            "path": "oekofen/wartung_vorbereiten.yaml",
            "input": {
                "kalender": "calendar.ofen_wartung",
                "anlage_select": "select.heizraum_ofen_anlage_betriebsart",
                "aus_option": "Aus",
                "stichworte": "Rauchfangkehrer, Service Ofen",
                "uhrzeit": "20:00:00",
                "szene_id": "oekofen_zustand_vor_wartung",
                "benachrichtigung": "notify.handy",
            },
        }
    }
    automation_component = MagicMock()
    automation_component.entities = [automation_entity]
    hass.data = {AUTOMATION_DATA_COMPONENT: automation_component}

    view = await async_build_wartung_view(hass)

    entities_card = next(c for c in view["cards"] if c.get("type") == "entities")
    assert entities_card["entities"][0] == "automation.oekofen_wartung_vorbereiten"
    assert "select.heizraum_ofen_anlage_betriebsart" in entities_card["entities"]
    assert any(
        isinstance(e, dict) and e.get("entity") == "scene.oekofen_zustand_vor_wartung"
        for e in entities_card["entities"]
    )

    info_card = next(c for c in view["cards"] if "notify.handy" in c.get("content", ""))
    assert "20:00" in info_card["content"]
    assert "Rauchfangkehrer" in info_card["content"]


async def test_async_build_wartung_view_detects_hand_written_shutdown_automation():
    """Not every user imports the actual Blueprint - some write the
    equivalent automation by hand instead (real-world regression: a live
    deployment had exactly this "Ofen: Vor Wartungstermin ausschalten"
    automation, hand-written with the same scene.create + select.select_option
    + notify.send_message shape, and got nothing on the Wartung tab because
    automations_with_blueprint() naturally found no Blueprint-based match).
    This must be detected too, best-effort, from the automation's own
    raw_config."""
    from homeassistant.components.automation import DATA_COMPONENT as AUTOMATION_DATA_COMPONENT

    hass = MagicMock()
    calendar_state = fake_state("on", friendly_name="Ofen Wartung")
    calendar_state.entity_id = "calendar.ofen_wartung"
    scene_state = fake_state("2026-09-05T20:00:00+00:00")
    hass.states.async_all.return_value = [calendar_state]
    hass.states.get.side_effect = lambda eid: {
        "calendar.ofen_wartung": calendar_state,
        "scene.oekofen_zustand_vor_wartung": scene_state,
    }.get(eid)
    hass.services.async_call = AsyncMock(return_value={"calendar.ofen_wartung": {"events": []}})

    automation_entity = MagicMock()
    automation_entity.entity_id = "automation.ofen_vor_wartungstermin_ausschalten"
    automation_entity.referenced_blueprint = None
    automation_entity.raw_config = {
        "alias": "Ofen: Vor Wartungstermin ausschalten",
        "trigger": [{"platform": "time", "at": "20:00:00"}],
        "condition": [],
        "action": [
            {
                "action": "calendar.get_events",
                "target": {"entity_id": "calendar.ofen_wartung"},
                "response_variable": "kalender_morgen",
            },
            {
                "if": [{"condition": "template", "value_template": "{{ True }}"}],
                "then": [
                    {
                        "action": "scene.create",
                        "data": {
                            "scene_id": "oekofen_zustand_vor_wartung",
                            "snapshot_entities": ["select.heizraum_ofen_anlage_betriebsart"],
                        },
                    },
                    {
                        "action": "select.select_option",
                        "target": {"entity_id": "select.heizraum_ofen_anlage_betriebsart"},
                        "data": {"option": "Aus"},
                    },
                    {
                        "action": "notify.send_message",
                        "target": {"entity_id": "notify.pixel_10_pro_xl"},
                        "data": {"title": "ÖkOfen: Wartung vorbereitet", "message": "..."},
                    },
                ],
            },
        ],
    }
    automation_component = MagicMock()
    automation_component.entities = [automation_entity]
    hass.data = {AUTOMATION_DATA_COMPONENT: automation_component}

    view = await async_build_wartung_view(hass)

    entities_card = next(c for c in view["cards"] if c.get("type") == "entities")
    assert entities_card["entities"][0] == "automation.ofen_vor_wartungstermin_ausschalten"
    assert "select.heizraum_ofen_anlage_betriebsart" in entities_card["entities"]
    assert any(
        isinstance(e, dict) and e.get("entity") == "scene.oekofen_zustand_vor_wartung"
        for e in entities_card["entities"]
    )
    info_card = next(c for c in view["cards"] if "pixel_10_pro_xl" in c.get("content", ""))
    assert "20:00" in info_card["content"]


async def test_async_build_wartung_view_hides_restore_row_when_scene_not_yet_created():
    """scene.create only runs the first time the shutdown automation
    actually fires - before that, scene.<szene_id> doesn't exist yet.
    Showing it anyway used to render as a scary "Entität nicht gefunden"
    warning in the entities card (live-reported UX issue); the row must be
    omitted entirely until the scene actually exists."""
    from homeassistant.components.automation import DATA_COMPONENT as AUTOMATION_DATA_COMPONENT

    hass = MagicMock()
    calendar_state = fake_state("on", friendly_name="Ofen Wartung")
    calendar_state.entity_id = "calendar.ofen_wartung"
    hass.states.async_all.return_value = [calendar_state]
    hass.states.get.side_effect = lambda eid: calendar_state if eid == "calendar.ofen_wartung" else None
    hass.services.async_call = AsyncMock(return_value={"calendar.ofen_wartung": {"events": []}})

    automation_entity = MagicMock()
    automation_entity.entity_id = "automation.oekofen_wartung_vorbereiten"
    automation_entity.referenced_blueprint = "oekofen/wartung_vorbereiten.yaml"
    automation_entity._blueprint_inputs = {
        "use_blueprint": {
            "path": "oekofen/wartung_vorbereiten.yaml",
            "input": {
                "anlage_select": "select.heizraum_ofen_anlage_betriebsart",
                "szene_id": "oekofen_zustand_vor_wartung",
                "benachrichtigung": "notify.handy",
                "uhrzeit": "20:00:00",
            },
        }
    }
    automation_component = MagicMock()
    automation_component.entities = [automation_entity]
    hass.data = {AUTOMATION_DATA_COMPONENT: automation_component}

    view = await async_build_wartung_view(hass)

    entities_card = next(c for c in view["cards"] if c.get("type") == "entities")
    assert not any(
        isinstance(e, dict) and e.get("entity") == "scene.oekofen_zustand_vor_wartung"
        for e in entities_card["entities"]
    )
    assert "scene.oekofen_zustand_vor_wartung" not in entities_card["entities"]


async def test_async_build_wartung_view_omits_automation_cards_when_none_configured():
    """No "wartung_vorbereiten" blueprint automation configured -> no extra
    cards, just the plain calendar view (regression guard: this must not
    raise even though hass.data here has no automation component at all)."""
    hass = MagicMock()
    calendar_state = fake_state("on", friendly_name="Ofen Wartung")
    calendar_state.entity_id = "calendar.ofen_wartung"
    hass.states.async_all.return_value = [calendar_state]
    hass.states.get.return_value = calendar_state
    hass.services.async_call = AsyncMock(return_value={"calendar.ofen_wartung": {"events": []}})
    hass.data = {}

    view = await async_build_wartung_view(hass)

    assert len(view["cards"]) == 2
    assert not any(c.get("type") == "entities" for c in view["cards"])


def _patch_lovelace_collaborators(collection_instance, storage_instance):
    """Patch the HA core lovelace internals async_regenerate_dashboard reaches
    into: a throwaway DashboardsCollection (since real one isn't reachable via
    hass.data - see _async_create_and_register_dashboard's docstring),
    LovelaceStorage, and the frontend panel registry."""
    return (
        patch(
            "custom_components.oekofen.dashboard.lovelace_dashboard.DashboardsCollection",
            return_value=collection_instance,
        ),
        patch(
            "custom_components.oekofen.dashboard.lovelace_dashboard.LovelaceStorage",
            return_value=storage_instance,
        ),
        patch("custom_components.oekofen.dashboard.frontend.async_panel_exists", return_value=False),
        patch("custom_components.oekofen.dashboard.frontend.async_register_built_in_panel"),
    )


async def test_async_regenerate_dashboard_creates_dashboard_once():
    """The first call creates the dashboard item (visible in the sidebar);
    every later call must just overwrite its content, not try (and fail) to
    create it again."""
    hass = MagicMock()
    hass.data = {}
    hass.states.async_all.return_value = []

    dashboards = {}
    hass.data["lovelace"] = SimpleNamespace(dashboards=dashboards)

    store = MagicMock()
    store.async_save = AsyncMock()

    collection_instance = MagicMock()
    collection_instance.async_load = AsyncMock()
    collection_instance.async_items = MagicMock(return_value=[])
    collection_instance.async_create_item = AsyncMock(
        return_value={"id": DASHBOARD_URL_PATH, "url_path": DASHBOARD_URL_PATH}
    )

    empty_device_registry = MagicMock(devices=MagicMock(values=lambda: []))
    patches = _patch_lovelace_collaborators(collection_instance, store)
    with patch("custom_components.oekofen.dashboard.dr.async_get", return_value=empty_device_registry), patch(
        "custom_components.oekofen.dashboard.er.async_get", return_value=MagicMock()
    ), patches[0], patches[1], patches[2], patches[3]:
        await async_regenerate_dashboard(hass)
        await async_regenerate_dashboard(hass)

    collection_instance.async_create_item.assert_awaited_once()
    assert store.async_save.await_count == 2


async def test_async_regenerate_dashboard_allows_single_word_url_path():
    """DASHBOARD_URL_PATH ("oekofen") has no hyphen - HA core's
    DashboardsCollection._process_create_data rejects that unless
    allow_single_word is explicitly set, so the create payload must include
    it (regression test: this raised vol.Invalid in production once the
    LovelaceData/dashboards_collection access itself was fixed)."""
    hass = MagicMock()
    hass.data = {}
    hass.states.async_all.return_value = []

    dashboards = {}
    hass.data["lovelace"] = SimpleNamespace(dashboards=dashboards)

    store = MagicMock()
    store.async_save = AsyncMock()

    collection_instance = MagicMock()
    collection_instance.async_load = AsyncMock()
    collection_instance.async_items = MagicMock(return_value=[])
    collection_instance.async_create_item = AsyncMock(
        return_value={"id": DASHBOARD_URL_PATH, "url_path": DASHBOARD_URL_PATH}
    )

    empty_device_registry = MagicMock(devices=MagicMock(values=lambda: []))
    patches = _patch_lovelace_collaborators(collection_instance, store)
    with patch("custom_components.oekofen.dashboard.dr.async_get", return_value=empty_device_registry), patch(
        "custom_components.oekofen.dashboard.er.async_get", return_value=MagicMock()
    ), patches[0], patches[1], patches[2], patches[3]:
        await async_regenerate_dashboard(hass)

    payload = collection_instance.async_create_item.call_args[0][0]
    assert payload["allow_single_word"] is True
    assert payload["url_path"] == DASHBOARD_URL_PATH
