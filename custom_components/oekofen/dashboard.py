"""Server-side generator for the auto-managed ÖkOfen Lovelace dashboard.

This is a Python port of the view-building logic that used to live in
www/oekofen-strategy.js, a client-side Lovelace "dashboard strategy". That
approach had a structural flaw: HA's frontend gives a custom strategy
element only a few seconds to register itself after every single page load,
and a slow/cold-started client (a kiosk tablet reconnecting right after an
HA restart, in particular) can lose that race - "Timeout waiting for
strategy element ... to be registered" - with no way to recover short of a
fully fresh page load. Two rounds of increasingly careful client-side
caching fixes (see git history around 0.9.2-0.9.8) narrowed the window but
could never close it, because the failure mode is inherent to depending on
a client-side custom element registering itself in time at all.

Generating a plain, static `views: [...]` Lovelace config here instead and
saving it via the "lovelace" integration's own storage API (the same
mechanism HA core itself uses to auto-create the onboarding "map"
dashboard) sidesteps the whole problem: there is no custom element to
register, no timeout to race, nothing for a client to get stuck waiting
on. HA's frontend renders it exactly like any hand-authored dashboard,
identically on every single load - a brand new tab, a kiosk tablet
reconnecting mid-restart, or a client that has never talked to this HA
instance before all get the same reliable result. Every card type used
below (markdown, tile, grid, vertical/horizontal-stack, entities,
thermostat with features, calendar, history-graph, statistics-graph) is a
Lovelace card built into HA core - none of them need a HACS frontend
resource, so this integration no longer registers or ships any JS at all.

The cost of this approach: the view *structure* (which circuits/sections
exist, which fields are installer-only, which calendar is the maintenance
one) is fixed at the moment async_regenerate_dashboard() runs, not
recomputed live in the browser on every page load. That only matters for
things that change the structure itself (a firmware switch flipping which
smart/classic entities have real data, a newly added maintenance
appointment). See __init__.py for when regeneration is triggered.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Not the integration's own hass.data[DOMAIN] key on purpose - importing
# DOMAIN from __init__.py here would import this module circularly (that's
# the one importing this one). A private key scoped to this module only is
# simpler than restructuring around it.
_LOCK_KEY = "_oekofen_dashboard_lock"

DASHBOARD_URL_PATH = "oekofen"
DASHBOARD_TITLE = "ÖkOfen"
DASHBOARD_ICON = "mdi:home-thermometer"

DAYS = ["sonntag", "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag"]
DAY_LABELS = {
    "sonntag": "So",
    "montag": "Mo",
    "dienstag": "Di",
    "mittwoch": "Mi",
    "donnerstag": "Do",
    "freitag": "Fr",
    "samstag": "Sa",
}
PROGRAMS = [1, 2]
BLOCKS = [1, 2, 3]

CIRCUIT_META = {
    "heizkreis": {"label": "Heizkreis", "icon": "mdi:radiator", "emoji": "\U0001F3E0", "hasZeitprogramm": True, "hasClimate": True},
    "warmwasser": {"label": "Warmwasser", "icon": "mdi:water-boiler", "emoji": "\U0001F4A7", "hasZeitprogramm": True, "hasClimate": True},
    "pellematic": {"label": "Pellematic", "icon": "mdi:fire", "emoji": "\U0001F525", "hasZeitprogramm": False, "hasClimate": True},
    "zirkulationspumpe": {"label": "Zirkulationspumpe", "icon": "mdi:pump", "emoji": "\U0001F504", "hasZeitprogramm": True, "hasClimate": False},
}

# Buffer-tank probes and the supply/circulation pump are top-level sensors
# with no "<type>_<index>_" structure, so they never match a circuit and
# would otherwise get dumped into the Übersicht's generic sensor list. Pull
# them into their own view instead - matched by name (against sensor.py's
# actual SENSOR_DEFINITIONS keys: buffer_*, supply_pump,
# circulation_pump_speed) since, unlike device_class/state_class, nothing
# in the entity registry distinguishes "this sensor is about the buffer
# tank".
PUFFER_PUMPEN_RE = re.compile(r"^(buffer_\w*|supply_pump|circulation_pump_speed)$")
PUFFER_PUMPEN_LABELS = {
    "buffer_top_temperature": "Puffer Oben Ist",
    "buffer_top_target_temperature": "Puffer Oben Soll",
    "buffer_bottom_temperature": "Puffer Unten Ist",
    "buffer_bottom_target_temperature": "Puffer Unten Soll",
    "buffer_pump": "Pufferpumpe",
    "supply_pump": "Zubringerpumpe",
    "circulation_pump_speed": "Zirkulationspumpe Drehzahl",
}
DURATION_UNITS = {"h", "min", "s", "zs"}

CIRCUIT_RE = re.compile(r"^(heizkreis|warmwasser|pellematic|zirkulationspumpe)_(\d+)(?:_(.*))?$")
ORDERED_TYPES = ["heizkreis", "warmwasser", "pellematic", "zirkulationspumpe"]


def domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def object_id_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[1]


def common_prefix(object_ids: list[str]) -> str:
    """Longest common prefix across all object_ids, trimmed back to the last "_"."""
    if not object_ids:
        return ""
    prefix = object_ids[0]
    for s in object_ids[1:]:
        j = 0
        max_len = min(len(prefix), len(s))
        while j < max_len and prefix[j] == s[j]:
            j += 1
        prefix = prefix[:j]
        if not prefix:
            break
    cut = prefix.rfind("_")
    return prefix[: cut + 1] if cut >= 0 else ""


@dataclass
class Circuit:
    type: str
    index: int
    suffix: str
    entities: dict[str, str] = field(default_factory=dict)  # "domain:relative" -> entity_id

    def domain_entities(self, domain: str) -> list[str]:
        out = [eid for key, eid in self.entities.items() if key.startswith(f"{domain}:")]
        out.sort()
        return out

    def entity(self, domain: str, suffix: str) -> str | None:
        return self.entities.get(f"{domain}:{suffix}")


@dataclass
class AnalyzeResult:
    prefix: str
    circuits: list[Circuit]
    leftover: list[str]


def analyze_entities(entity_ids: list[str]) -> AnalyzeResult:
    """Group a device's entity_ids into a shared prefix, circuits, and leftovers."""
    object_ids = [object_id_of(e) for e in entity_ids]
    prefix = common_prefix(object_ids)

    by_suffix: dict[str, str] = {}
    for entity_id, obj_id in zip(entity_ids, object_ids):
        suffix = obj_id[len(prefix):] if obj_id.startswith(prefix) else obj_id
        by_suffix[f"{domain_of(entity_id)}:{suffix}"] = entity_id

    circuits: dict[str, Circuit] = {}
    for key in by_suffix:
        suffix = key.split(":", 1)[1]
        m = CIRCUIT_RE.match(suffix)
        if not m:
            continue
        circuit_type, index = m.group(1), m.group(2)
        circuit_key = f"{circuit_type}_{index}"
        if circuit_key not in circuits:
            circuits[circuit_key] = Circuit(type=circuit_type, index=int(index), suffix=circuit_key)

    circuit_list = sorted(
        circuits.values(),
        key=lambda c: (ORDERED_TYPES.index(c.type) if c.type in ORDERED_TYPES else len(ORDERED_TYPES), c.index),
    )

    claimed: set[str] = set()
    for circuit in circuit_list:
        circuit_prefix = f"{circuit.suffix}_"
        for key, entity_id in by_suffix.items():
            domain, suffix = key.split(":", 1)
            relative: str | None = None
            if suffix == circuit.suffix:
                relative = ""
            elif suffix.startswith(circuit_prefix):
                relative = suffix[len(circuit_prefix):]
            if relative is not None:
                circuit.entities[f"{domain}:{relative}"] = entity_id
                claimed.add(key)

    leftover = sorted(eid for key, eid in by_suffix.items() if key not in claimed)

    return AnalyzeResult(prefix=prefix, circuits=circuit_list, leftover=leftover)


def tile(entity: str, name: str | None = None, icon: str | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {"type": "tile", "entity": entity}
    if name:
        card["name"] = name
    if icon:
        card["icon"] = icon
    return card


def grid(cards: list[dict[str, Any]], columns: int = 2) -> dict[str, Any]:
    return {"type": "grid", "columns": columns, "square": False, "cards": cards}


def markdown(content: str) -> dict[str, Any]:
    return {"type": "markdown", "content": content}


def stack(cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "vertical-stack", "cards": cards}


def phase_duration_cards(title: str, ids: list[str], extra_history_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """7-day history-graph + 90-day mean/min/max statistics-graph pair for a Kesselstatus phase-duration sensor."""
    if not ids:
        return []
    history_ids = [*ids, *extra_history_ids] if extra_history_ids else ids
    return [
        {
            "type": "history-graph",
            "title": title,
            "hours_to_show": 168,
            "refresh_interval": 60,
            "entities": [{"entity": i} for i in history_ids],
        },
        {
            "type": "statistics-graph",
            "title": f"{title} (Langzeit, 90 Tage)",
            "entities": [{"entity": i} for i in ids],
            "days_to_show": 90,
            "period": "day",
            "stat_types": ["mean", "min", "max"],
        },
    ]


def installer_warning_of(entity_id: str, states: dict[str, State]) -> str | None:
    """number.py/select.py tag installer-only fields (protected by a technician
    PIN on the real device) with a "warnhinweis" state attribute - surface it
    here instead of leaving it buried in the entity's attributes, where
    nobody but a Developer Tools user would ever see it."""
    state = states.get(entity_id)
    if state is None:
        return None
    return state.attributes.get("warnhinweis")


_ZEIT_RE = re.compile(r"_zeit_\d+_")


def build_settings_grid(
    circuit: Circuit, used_entity_ids: list[str | None], states: dict[str, State]
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    """Settings grid: every number/select entity of the circuit not already
    used elsewhere, split into normal fields and installer-only ones."""
    used = {e for e in used_entity_ids if e}
    normal: list[str] = []
    warned: list[str] = []
    warning_text: str | None = None
    for domain in ("number", "select"):
        for entity_id in circuit.domain_entities(domain):
            if entity_id in used:
                continue
            # Zeitprogramm/day-schedule entities are handled in their own section.
            if _ZEIT_RE.search(object_id_of(entity_id)):
                continue
            hint = installer_warning_of(entity_id, states)
            if hint:
                warned.append(entity_id)
                if not warning_text:
                    warning_text = hint
            else:
                normal.append(entity_id)
    return [tile(i) for i in normal], warned, warning_text


def build_zeitprogramm_section(circuit: Circuit) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = [
        markdown(f"## \U0001F552 Zeitprogramme - {CIRCUIT_META[circuit.type]['label']} {circuit.index}")
    ]
    for program in PROGRAMS:
        day_tiles = []
        time_entities = []
        any_found = False
        for day in DAYS:
            switch_entity = circuit.entity("switch", f"zeit_{program}_{day}_aktiv")
            if switch_entity:
                any_found = True
                day_tiles.append(tile(switch_entity, DAY_LABELS[day], "mdi:calendar-check"))
            for block in BLOCKS:
                von = circuit.entity("time", f"zeit_{program}_{day}_block_{block}_von")
                bis = circuit.entity("time", f"zeit_{program}_{day}_block_{block}_bis")
                if von:
                    time_entities.append({"entity": von, "name": f"{DAY_LABELS[day]} Block {block} Von", "icon": "mdi:clock-start"})
                if bis:
                    time_entities.append({"entity": bis, "name": f"{DAY_LABELS[day]} Block {block} Bis", "icon": "mdi:clock-end"})
        if not any_found:
            continue
        program_cards = [markdown(f"### Zeit {program}"), grid(day_tiles, 7)]
        if time_entities:
            program_cards.append({"type": "entities", "entities": time_entities})
        cards.append(stack(program_cards))
    return [stack(cards)] if len(cards) > 1 else []


_EXTRA_FIELDS = [
    ("partyprogramm", "Party aktiv", "mdi:party-popper"),
    ("party_endzeit", "Party Endzeit", "mdi:clock-end"),
    ("urlaubsprogramm", "Urlaub aktiv", "mdi:airplane"),
    ("urlaub_start", "Urlaub Start", "mdi:airplane-takeoff"),
    ("urlaub_ende", "Urlaub Ende", "mdi:airplane-landing"),
    ("einmal_aufbereiten", "Einmal Aufbereiten", "mdi:water-boiler-auto"),
    ("vorrang", "Vorrang", "mdi:priority-high"),
    ("legionellenschutz", "Legionellenschutz", "mdi:shield-check"),
]


def build_circuit_view(circuit: Circuit, states: dict[str, State]) -> dict[str, Any]:
    meta = CIRCUIT_META[circuit.type]
    title = f"{meta['label']} {circuit.index}"
    used_for_settings: list[str | None] = []
    top_cards: list[dict[str, Any]] = []

    if meta["hasClimate"]:
        climate_entity = circuit.entity("climate", "")
        if climate_entity:
            top_cards.append(markdown(f"## {meta['emoji']} {title}"))
            # Neither hvac_mode (Aus/Auto/Heizen) nor preset_mode (Heizkreis
            # "Absenken", Warmwasser "Boost") are shown directly on a plain
            # thermostat card - both were only reachable through the
            # more-info dialog. Card features add them as inline buttons
            # instead. Every circuit with a climate entity has hvac_modes;
            # only Heizkreis/Warmwasser have presets (Pellematic has none,
            # see mode_map in climate.py).
            features = [{"type": "climate-hvac-modes"}]
            if circuit.type in ("heizkreis", "warmwasser"):
                features.append({"type": "climate-preset-modes"})
            top_cards.append({"type": "thermostat", "entity": climate_entity, "features": features})
            used_for_settings.append(climate_entity)

    mode_select = circuit.entity("select", "betriebsart")
    if mode_select:
        used_for_settings.append(mode_select)
    zeitprogramm_select = circuit.entity("select", "aktives_zeitprogramm")
    if zeitprogramm_select:
        used_for_settings.append(zeitprogramm_select)

    quick_cards = []
    if not top_cards:
        top_cards.append(markdown(f"## {title}"))
    if mode_select:
        quick_cards.append(tile(mode_select, "Betriebsart"))
    if zeitprogramm_select:
        quick_cards.append(tile(zeitprogramm_select, "Zeitprogramm"))
    if quick_cards:
        top_cards.append(grid(quick_cards, 2))

    card_stacks = [stack(top_cards)]

    # Party/Urlaub (Heizkreis) and Einmal Aufbereiten (Warmwasser) fields,
    # if present - looked up (and reserved via used_for_settings) *before*
    # build_settings_grid runs below, so it doesn't also render them as
    # generic settings tiles. Installer-only fields among these (e.g.
    # Vorrang, Legionellenschutz) go into the warning section instead of
    # the Party/Urlaub card.
    extra_cards = []
    extra_warned_ids: list[str] = []
    extra_warning_text: str | None = None
    for suffix, name, icon in _EXTRA_FIELDS:
        entity_id = circuit.entity("switch", suffix) or circuit.entity("datetime", suffix) or circuit.entity("select", suffix)
        if entity_id:
            hint = installer_warning_of(entity_id, states)
            if hint:
                extra_warned_ids.append(entity_id)
                if not extra_warning_text:
                    extra_warning_text = hint
            else:
                extra_cards.append(tile(entity_id, name, icon))
            used_for_settings.append(entity_id)

    settings_cards, warned_ids, settings_warning_text = build_settings_grid(circuit, used_for_settings, states)
    if settings_cards:
        card_stacks.append(stack([markdown(f"## ⚙️ Einstellungen {title}"), grid(settings_cards, 2)]))
    warned_ids = [*warned_ids, *extra_warned_ids]
    warning_text = settings_warning_text or extra_warning_text

    if warned_ids:
        card_stacks.append(
            stack([
                markdown(f"## ⚠️ Installateur-Ebene {title}\n\n{warning_text}"),
                grid([tile(i) for i in warned_ids], 2),
            ])
        )

    if extra_cards:
        card_stacks.append(stack([markdown("## \U0001F389 Party / Urlaub"), grid(extra_cards, 2)]))

    if meta["hasZeitprogramm"]:
        card_stacks.extend(build_zeitprogramm_section(circuit))

    return {
        "title": title,
        "path": circuit.suffix.replace("_", "-"),
        "icon": meta["icon"],
        "cards": card_stacks,
    }


_INTEGRATION_VERSION_RE = re.compile(r"integration_version$")
_DOMAIN_TITLES = {
    "select": "\U0001F39B️ Weitere Betriebsarten",
    "number": "⚙️ Weitere Einstellungen",
    "switch": "\U0001F50C Weitere Schalter",
    "datetime": "\U0001F552 Datum & Uhrzeit",
}


def build_overview_views(circuits: list[Circuit], leftover_entity_ids: list[str], states: dict[str, State]) -> list[dict[str, Any]]:
    """Übersicht plus two dedicated views split out of it: Diagnose (sensor
    leftovers) and Mail/SMTP (text leftovers) each get long entity lists
    that don't belong sharing a page with everything else."""
    cards: list[dict[str, Any]] = []

    # Surface the installed integration version at the very top of the
    # dashboard instead of leaving it buried in the generic Diagnose list -
    # lets you confirm at a glance which version is actually running.
    version_id = next((i for i in leftover_entity_ids if _INTEGRATION_VERSION_RE.search(object_id_of(i))), None)
    if version_id:
        leftover_entity_ids = [i for i in leftover_entity_ids if i != version_id]
        state = states.get(version_id)
        if state:
            cards.append(markdown(f"*ÖkOfen Integration v{state.state}*"))

    mode_cards = []
    for circuit in circuits:
        mode_select = circuit.entity("select", "betriebsart")
        climate_entity = circuit.entity("climate", "")
        entity = mode_select or climate_entity
        if entity:
            mode_cards.append(tile(entity, f"{CIRCUIT_META[circuit.type]['label']} {circuit.index}", CIRCUIT_META[circuit.type]["icon"]))
    if mode_cards:
        cards.append(stack([markdown("## \U0001F527 Betriebsarten"), grid(mode_cards, 2)]))

    by_domain: dict[str, list[str]] = {}
    for entity_id in leftover_entity_ids:
        by_domain.setdefault(domain_of(entity_id), []).append(entity_id)

    for domain, ids in by_domain.items():
        if domain not in _DOMAIN_TITLES:
            continue
        cards.append(
            stack([markdown(f"## {_DOMAIN_TITLES[domain]}"), {"type": "entities", "entities": [{"entity": e} for e in ids]}])
        )

    views = [{"title": "Übersicht", "path": "overview", "icon": "mdi:home-thermometer", "cards": cards}]

    diagnose_ids = by_domain.get("sensor")
    if diagnose_ids:
        views.append({
            "title": "Diagnose",
            "path": "diagnose",
            "icon": "mdi:magnify-scan",
            "cards": [{"type": "entities", "entities": [{"entity": e} for e in diagnose_ids]}],
        })

    mail_ids = by_domain.get("text")
    if mail_ids:
        views.append({
            "title": "Mail / SMTP",
            "path": "mail-smtp",
            "icon": "mdi:email-outline",
            "cards": [{"type": "entities", "entities": [{"entity": e} for e in mail_ids]}],
        })

    return views


def puffer_pumpen_label(suffix: str) -> str:
    return PUFFER_PUMPEN_LABELS.get(suffix, suffix.replace("_", " "))


def build_puffer_pumpen_view(entity_ids: list[str], prefix: str) -> dict[str, Any]:
    """Buffer-tank probes and circulation-pump sensors, split out of the leftover bucket."""
    cards = []
    for entity_id in entity_ids:
        suffix = object_id_of(entity_id)[len(prefix):]
        icon = "mdi:pump" if "pump" in suffix else "mdi:thermometer"
        cards.append(tile(entity_id, puffer_pumpen_label(suffix), icon))
    return {
        "title": "Puffer & Pumpen",
        "path": "puffer-pumpen",
        "icon": "mdi:water-pump",
        "cards": [stack([markdown("## \U0001F5C4️ Puffer & Pumpen"), grid(cards, 2)])],
    }


_FEUERRAUM_RE = re.compile(r"feuerraumtemperatur")
_ZUENDZEIT_RE = re.compile(r"gluhstab_zundzeit")
_SAUGDAUER_RE = re.compile(r"saugdauer")
_SOFTSTARTDAUER_RE = re.compile(r"softstartdauer")
_NACHLAUFDAUER_RE = re.compile(r"nachlaufdauer")
_WARNSCHWELLE_RE = re.compile(r"gluhstab_warnschwelle")


def build_statistik_view(entity_ids: list[str], states: dict[str, State]) -> dict[str, Any] | None:
    """History/statistics graphs, derived purely from each sensor's
    device_class/state_class/unit (via states) - not from entity names, so
    it generalizes to whatever sensors a given device exposes."""
    sensor_ids = [i for i in entity_ids if domain_of(i) == "sensor" and i in states]

    temp_ids = sorted(i for i in sensor_ids if states[i].attributes.get("device_class") == "temperature")
    # Feuerraumtemperatur (combustion-chamber probe) and its setpoint run
    # 0-1000 degC, an order of magnitude above every other temperature
    # sensor - sharing one chart's y-axis flattens those into an unreadable
    # straight line. Split it into its own chart instead.
    feuerraum_ids = [i for i in temp_ids if _FEUERRAUM_RE.search(object_id_of(i))]
    normal_temp_ids = [i for i in temp_ids if i not in feuerraum_ids]
    counter_ids = [i for i in sensor_ids if states[i].attributes.get("state_class") == "total_increasing"]
    counter_count_ids = sorted(i for i in counter_ids if not states[i].attributes.get("unit_of_measurement"))
    counter_time_ids = sorted(i for i in counter_ids if states[i].attributes.get("unit_of_measurement") in DURATION_UNITS)
    # Zündzeit/Saugdauer/Softstartdauer/Nachlaufdauer update irregularly
    # (once per completed phase, hours or days apart) rather than
    # accumulating daily like the runtime/cycle counters below - a trend
    # line of their own values over time is the useful view, not a per-day
    # change bar chart.
    zuendzeit_ids = [i for i in sensor_ids if _ZUENDZEIT_RE.search(object_id_of(i))]
    saugdauer_ids = [i for i in sensor_ids if _SAUGDAUER_RE.search(object_id_of(i))]
    softstartdauer_ids = [i for i in sensor_ids if _SOFTSTARTDAUER_RE.search(object_id_of(i))]
    nachlaufdauer_ids = [i for i in sensor_ids if _NACHLAUFDAUER_RE.search(object_id_of(i))]
    phase_duration_buckets = [zuendzeit_ids, saugdauer_ids, softstartdauer_ids, nachlaufdauer_ids]

    def _is_stats_tile(entity_id: str) -> bool:
        if any(entity_id in bucket for bucket in phase_duration_buckets):
            return False
        a = states[entity_id].attributes
        if a.get("device_class") == "temperature":
            return False
        return a.get("device_class") == "duration" or a.get("unit_of_measurement") in DURATION_UNITS or a.get("state_class") == "total_increasing"

    stats_tile_ids = sorted(i for i in sensor_ids if _is_stats_tile(i))

    if not temp_ids and not stats_tile_ids and not any(phase_duration_buckets):
        return None

    cards: list[dict[str, Any]] = []

    if stats_tile_ids:
        cards.append(stack([markdown("## ⏱️ Betriebsstunden & Zyklen"), grid([tile(i) for i in stats_tile_ids], 2)]))

    if normal_temp_ids:
        cards.append({
            "type": "history-graph", "title": "Temperaturverlauf", "hours_to_show": 24, "refresh_interval": 60,
            "entities": [{"entity": i} for i in normal_temp_ids],
        })
        cards.append({
            "type": "statistics-graph", "title": "Temperaturverlauf (Langzeit, 90 Tage)",
            "entities": [{"entity": i} for i in normal_temp_ids],
            "days_to_show": 90, "period": "day", "stat_types": ["mean", "min", "max"],
        })

    if feuerraum_ids:
        cards.append({
            "type": "history-graph", "title": "Feuerraumtemperatur", "hours_to_show": 24, "refresh_interval": 60,
            "entities": [{"entity": i} for i in feuerraum_ids],
        })
        cards.append({
            "type": "statistics-graph", "title": "Feuerraumtemperatur (Langzeit, 90 Tage)",
            "entities": [{"entity": i} for i in feuerraum_ids],
            "days_to_show": 90, "period": "day", "stat_types": ["mean", "min", "max"],
        })

    # The warning-threshold number entity has no long-term statistics of its
    # own (HA's recorder only compiles those for sensor state_class
    # entities), but its plain state history still works fine in a
    # history-graph, alongside the actual duration, as a reference line.
    warnschwelle_id = next((i for i in entity_ids if domain_of(i) == "number" and _WARNSCHWELLE_RE.search(object_id_of(i))), None)
    cards.extend(phase_duration_cards("Zündzeit", zuendzeit_ids, [warnschwelle_id] if warnschwelle_id else None))
    cards.extend(phase_duration_cards("Saugdauer", saugdauer_ids))
    cards.extend(phase_duration_cards("Softstartdauer", softstartdauer_ids))
    cards.extend(phase_duration_cards("Nachlaufdauer", nachlaufdauer_ids))

    if counter_count_ids:
        cards.append({
            "type": "statistics-graph", "title": "Ereignisse pro Tag", "chart_type": "bar",
            "entities": [{"entity": i} for i in counter_count_ids],
            "days_to_show": 60, "period": "day", "stat_types": ["change"],
        })
    if counter_time_ids:
        cards.append({
            "type": "statistics-graph", "title": "Laufzeit pro Tag", "chart_type": "bar",
            "entities": [{"entity": i} for i in counter_time_ids],
            "days_to_show": 60, "period": "day", "stat_types": ["change"],
        })

    return {"title": "Statistik", "path": "statistik", "icon": "mdi:chart-line", "cards": cards}


# date.weekday(): Monday=0 ... Sunday=6. strftime("%a") depends on the
# process locale (typically English on a stock HA install, "Thu" not "Do"),
# so spell the German abbreviations out instead of relying on it.
_WEEKDAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


async def async_build_wartung_view(hass: HomeAssistant) -> dict[str, Any] | None:
    """If a calendar entity looks like it's used for ÖkOfen maintenance
    appointments (see blueprints/automation/oekofen/), add a view with the
    next 3 upcoming events plus the native HA calendar card (which already
    has add/edit/delete built in for a locally-editable calendar) - not tied
    to any specific device."""
    calendar_ids = [s.entity_id for s in hass.states.async_all("calendar")]
    calendar_entity = next(
        (
            eid
            for eid in calendar_ids
            if matches_wartung(eid, hass.states.get(eid))
        ),
        None,
    )
    if not calendar_entity:
        return None

    start = dt_util.now()
    end = start + timedelta(days=180)
    try:
        response = await hass.services.async_call(
            "calendar",
            "get_events",
            {"entity_id": calendar_entity, "start_date_time": start, "end_date_time": end},
            blocking=True,
            return_response=True,
        )
    except Exception:
        # Fetching upcoming events is a nice-to-have on top of the native
        # calendar card below, not a reason to drop the whole "Wartung" tab
        # (and, since this whole function runs inside
        # async_build_dashboard_config with no caller-side try/except, an
        # unhandled error here would silently abort saving the *entire*
        # dashboard for this regeneration - not just this one view). A
        # transient failure right as the calendar entity itself first
        # appears (its own service may not be registered in the same
        # instant its state is) is exactly the case
        # async_track_state_added_domain's retrigger can otherwise hit.
        _LOGGER.warning("Could not fetch events for %s; showing calendar without a preview", calendar_entity, exc_info=True)
        response = None
    events = (response or {}).get(calendar_entity, {}).get("events", [])

    def _event_start(ev: dict[str, Any]) -> datetime:
        raw = ev.get("start")
        parsed = dt_util.parse_datetime(raw) or dt_util.parse_date(raw)
        return dt_util.as_utc(parsed) if isinstance(parsed, datetime) else dt_util.start_of_local_day(parsed)

    upcoming = sorted(events, key=_event_start)[:3]

    lines = []
    for ev in upcoming:
        raw = ev.get("start")
        parsed = dt_util.parse_datetime(raw)
        if parsed is not None:
            local = dt_util.as_local(parsed)
            datum = f"{_WEEKDAY_ABBR[local.weekday()]}, {local:%d.%m.%Y}"
            uhrzeit = local.strftime(" %H:%M")
        else:
            local = dt_util.parse_date(raw)
            datum = f"{_WEEKDAY_ABBR[local.weekday()]}, {local:%d.%m.%Y}" if local else raw
            uhrzeit = ""
        lines.append(f"- **{ev.get('summary')}** – {datum}{uhrzeit}")

    return {
        "title": "Wartung",
        "path": "wartung",
        # "mdi:calendar-wrench" doesn't exist in the MDI icon set - HA
        # silently renders no glyph at all for an unknown icon name rather
        # than erroring, so the tab still worked (reachable by URL,
        # correct content) but looked like blank, unclickable-seeming
        # space in the tab strip instead of a visible tab. "wrench" is a
        # foundational MDI icon, guaranteed to exist.
        "icon": "mdi:wrench",
        "cards": [
            markdown(f"## \U0001F5D3️ Nächste Termine\n\n" + ("\n".join(lines) if lines else "Keine anstehenden Termine.")),
            {"type": "calendar", "entities": [calendar_entity]},
        ],
    }


def matches_wartung(entity_id: str, state: State | None) -> bool:
    friendly_name = state.attributes.get("friendly_name", "") if state else ""
    name = f"{entity_id} {friendly_name}".lower()
    return "ofen" in name or "wartung" in name


async def async_build_dashboard_config(hass: HomeAssistant) -> dict[str, Any]:
    """Build the full {"views": [...]} config for every ÖkOfen device currently
    registered - the Python equivalent of oekofen-strategy.js's
    OekofenStrategy.generate()."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    target_devices = [
        d for d in device_registry.devices.values() if d.manufacturer == "ÖkOfen" and d.model == "Pellematic"
    ]

    if not target_devices:
        return {
            "views": [
                {
                    "title": "ÖkOfen",
                    "cards": [
                        markdown(
                            "## Kein ÖkOfen-Gerät gefunden\n\nPrüfe, ob die ha-oekofen-Integration eingerichtet ist."
                        )
                    ],
                }
            ]
        }

    states = hass.states
    all_states = {s.entity_id: s for s in states.async_all()}
    views: list[dict[str, Any]] = []
    multiple_devices = len(target_devices) > 1

    for device in target_devices:
        entity_ids = [
            e.entity_id for e in er.async_entries_for_device(entity_registry, device.id)
        ]
        result = analyze_entities(entity_ids)
        device_label = device.name_by_user or device.name or device.id
        device_slug = re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", str(device_label).lower()))

        puffer_pumpen_ids = []
        true_leftover = []
        for entity_id in result.leftover:
            suffix = object_id_of(entity_id)[len(result.prefix):]
            if domain_of(entity_id) == "sensor" and PUFFER_PUMPEN_RE.match(suffix):
                puffer_pumpen_ids.append(entity_id)
            else:
                true_leftover.append(entity_id)

        # build_overview_views returns [Übersicht, Diagnose?, Mail/SMTP?] -
        # keep Übersicht first, but push Diagnose/Mail-SMTP to the end
        # (after the circuits/Statistik): reference/meta pages, not
        # something checked as often as the circuit views.
        overview_view, *trailing_views = build_overview_views(result.circuits, true_leftover, all_states)
        device_views = [overview_view]
        if puffer_pumpen_ids:
            device_views.append(build_puffer_pumpen_view(puffer_pumpen_ids, result.prefix))
        device_views.extend(build_circuit_view(c, all_states) for c in result.circuits)
        statistik_view = build_statistik_view(entity_ids, all_states)
        if statistik_view:
            device_views.append(statistik_view)
        device_views.extend(trailing_views)
        if multiple_devices:
            for view in device_views:
                view["title"] = f"{device_label}: {view['title']}"
                view["path"] = f"{device_slug}-{view['path']}"
        views.extend(device_views)

    wartung_view = await async_build_wartung_view(hass)
    if wartung_view:
        views.append(wartung_view)

    return {"views": views}


async def _async_create_and_register_dashboard(hass: HomeAssistant, dashboards: dict) -> None:
    """Create the ÖkOfen dashboard entry and register its sidebar panel.

    HA core's lovelace integration keeps the live DashboardsCollection it
    uses internally (see lovelace/__init__.py's async_setup) as a plain
    local variable - it is never put into hass.data, so no other
    integration can call async_create_item on that exact instance. What IS
    shared and stable is the underlying storage file: DashboardsCollection
    always points at the same fixed Store key regardless of which instance
    constructs it. So we create our own throwaway DashboardsCollection here,
    async_load() it (reads that same file), and async_create_item() on it -
    that durably persists our entry into the same storage the real
    lovelace integration reads on every startup.

    Because our instance is separate, nothing else reacts to that write
    during *this* boot - so we also register the frontend panel and the
    in-memory dashboards[...] entry ourselves, right here. On every later
    boot, lovelace's own async_setup loads that same storage file itself
    and takes over registering the panel/dict entry through its normal
    code path - at which point DASHBOARD_URL_PATH is already present in
    `dashboards` and async_regenerate_dashboard's caller skips this
    function entirely, so there's no double-registration.
    """
    temp_collection = lovelace_dashboard.DashboardsCollection(hass)
    await temp_collection.async_load()

    item = next(
        (i for i in temp_collection.async_items() if i.get("url_path") == DASHBOARD_URL_PATH),
        None,
    )
    if item is None:
        item = await temp_collection.async_create_item({
            "url_path": DASHBOARD_URL_PATH,
            "title": DASHBOARD_TITLE,
            "icon": DASHBOARD_ICON,
            "show_in_sidebar": True,
            "require_admin": False,
            # DASHBOARD_URL_PATH ("oekofen") has no hyphen; lovelace's
            # DashboardsCollection._process_create_data rejects single-word
            # url_paths unless this is set.
            "allow_single_word": True,
        })

    dashboards[DASHBOARD_URL_PATH] = lovelace_dashboard.LovelaceStorage(hass, item)

    if not frontend.async_panel_exists(hass, DASHBOARD_URL_PATH):
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=DASHBOARD_URL_PATH,
            require_admin=False,
            show_in_sidebar=True,
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            config={"mode": "storage"},
        )


async def async_regenerate_dashboard(hass: HomeAssistant) -> None:
    """(Re)generate the auto-managed ÖkOfen dashboard and save it.

    Creates the dashboard (visible in the sidebar) the first time this
    runs; every later call just overwrites its content, the same way HA
    core auto-creates and fills the onboarding "map" dashboard.

    Guarded by a lock: with two ÖkOfen config entries set up concurrently
    (two physical devices), both would otherwise race to create the same
    dashboard - the second async_create_item call would find the url_path
    already taken and raise, exactly the class of "two concurrent callers
    step on each other" bug __init__.py's old frontend-registration code
    once had to guard against too.
    """
    lock: asyncio.Lock = hass.data.setdefault(_LOCK_KEY, asyncio.Lock())
    async with lock:
        lovelace_data = hass.data.get("lovelace")
        if lovelace_data is None:
            _LOGGER.debug("lovelace not set up yet; scheduling retry in 0.5s")
            async def _retry_lovelace():
                await asyncio.sleep(0.5)
                await async_regenerate_dashboard(hass)
            asyncio.create_task(_retry_lovelace())
            return

        # Since HA core 2024.5ish, hass.data["lovelace"] is a LovelaceData
        # dataclass (attribute access), not a plain dict - dict-style
        # access here raised AttributeError in production against a 2026.x
        # instance, even though it works fine against the older,
        # dict-shaped API this integration originally targeted.
        dashboards = getattr(lovelace_data, "dashboards", None)
        if dashboards is None and isinstance(lovelace_data, dict):
            dashboards = lovelace_data.get("dashboards")
        if dashboards is None:
            _LOGGER.debug("lovelace dashboards not initialized yet; scheduling retry in 0.5s")
            async def _retry():
                await asyncio.sleep(0.5)
                await async_regenerate_dashboard(hass)
            asyncio.create_task(_retry())
            return

        if DASHBOARD_URL_PATH not in dashboards:
            await _async_create_and_register_dashboard(hass, dashboards)

        config = await async_build_dashboard_config(hass)
        await dashboards[DASHBOARD_URL_PATH].async_save(config)
