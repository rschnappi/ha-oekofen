# ha-oekofen — Arbeitswissen für Claude Code

Home-Assistant-Custom-Integration für ÖkOfen-Pellematic-Heizungen. Läuft
gegen ein echtes, physisches Gerät beim Nutzer — Vorsicht bei Änderungen,
die Entity-Lifecycle/Coordinator-Timing berühren, siehe Vorfälle unten.

## Architektur

- **Ein gemeinsamer `DataUpdateCoordinator`** (`coordinator.py`, 15s-Intervall).
  Jede Plattform (`sensor.py`, `number.py`, `select.py`, `switch.py`,
  `time.py`, `datetime.py`, `climate.py`, `text.py`) registriert ihre
  benötigten Parameter über `coordinator.add_parameters(...)` im eigenen
  `async_setup_entry`, statt einen eigenen Coordinator zu bauen. Vorher (bis
  0.8.0) hatte jede Plattform ihren eigenen Coordinator — bis zu 11 separate
  Requests/Zyklus gegen den schwachbrüstigen Embedded-Webserver.
- **`__init__.py`'s `async_setup_entry`**: Reihenfolge ist absichtlich und
  fragil, wenn man sie ändert:
  1. `hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` —
     jede Plattform registriert ihre Parameter.
  2. `coordinator.async_refresh()` — **nicht**
     `async_config_entry_first_refresh()`. Letzteres wirft
     `ConfigEntryNotReady` bei Fehlschlag, was HA dazu bringt,
     `async_setup_entry` (inkl. `async_forward_entry_setups`) komplett neu
     zu versuchen, ohne die Plattformen des fehlgeschlagenen Versuchs
     abzumelden → `EntityComponent` wirft `ValueError: already been setup!`
     → Integration hängt dauerhaft in `SETUP_ERROR`. `async_refresh()` loggt
     nur und setzt `last_update_success = False`, Entities zeigen dann
     korrekt "nicht verfügbar" bis zum nächsten Poll (siehe PR #32).
  3. `_async_regenerate_dashboard_and_track_calendar(hass, entry)` **danach**,
     nicht davor — das generierte Dashboard hängt von echten Entity-Zuständen
     ab (`warnhinweis`-Attribute, Kalender-Termine), die vor dem ersten
     Refresh noch nicht existieren (siehe Frontend/Dashboard unten).
- **`coordinator.data` defaultet auf `{}`, nicht `None`** (überschrieben in
  `OekofenCoordinator.__init__`). Grund: Plattformen legen ihre Entities
  über `async_add_entities` an, *bevor* der erste Refresh läuft (siehe
  Reihenfolge oben) — `async_add_entities` wertet sofort `available`/
  `native_value` aus, was `parameter in coordinator.data` prüft. Gegen
  `None` crasht das (`TypeError`), gegen `{}` ist es einfach `False`. Ein
  gecrashtes Entity-Add hängt **dauerhaft** fest (nie als Listener
  registriert), auch nachdem der Coordinator später echte Daten hat. War die
  Ursache für einen kompletten Produktionsausfall (PR #29, direkt nach der
  Coordinator-Konsolidierung).

## Dual-Firmware-Muster (klassisch vs. "Smart")

Manche Parameter existieren in zwei Varianten je nach Firmware
(`L_pe_schnecke_sauganlage==4` = Smart). Etabliertes Muster (siehe
`number.py`, `climate.py`): **beide** Parameter registrieren, das Gerät
liefert nur für die tatsächlich aktive Variante echte Daten — welche das
ist, wird zur Laufzeit anhand von "hat einen Wert" entschieden, nicht
geraten/konfiguriert.

## Frontend/Dashboard (`dashboard.py`)

- **Bis 0.9.8**: eine clientseitige [Lovelace-Dashboard-Strategy](https://www.home-assistant.io/dashboards/strategies/)
  (`www/oekofen-strategy.js`), im Browser ausgeführt. Grundproblem, trotz
  mehrerer Anläufe (PR #30/#31/#38/#52) nie vollständig behoben: HA's
  Frontend gibt einem Custom-Strategy-Element nur wenige Sekunden Zeit,
  sich zu registrieren — ein kalt gestarteter Client (Kiosk-Tablet direkt
  nach einem HA-Neustart, langsames WLAN) kann dieses Rennen verlieren,
  unabhängig von Setup-Reihenfolge oder Caching-Headern. Ergebnis: „Timeout
  waiting for strategy element ... to be registered", reproduzierbar auch
  mit nachweislich korrekt ausgeliefertem, aktuellem JS.
- **Seit 0.10.0**: `dashboard.py` generiert dieselben Views **serverseitig
  in Python** (Port der alten `oekofen-strategy.js`-Logik, Funktion für
  Funktion) und speichert sie als ganz normales, statisches
  `{"views": [...]}`-Dashboard über HAs eigene Lovelace-Storage-API
  (`hass.data["lovelace"]["dashboards_collection"]`/`LovelaceStorage`
  — derselbe Mechanismus, mit dem HA selbst das Onboarding-Dashboard "Karte"
  anlegt, siehe `homeassistant/components/lovelace/__init__.py`s
  `_create_map_dashboard`). Kein Custom Element, kein Registrierungs-
  Timeout, keine JS-Datei mehr im Repo — jede verwendete Karte
  (`markdown`, `tile`, `grid`, `thermostat` mit `features`, `calendar`,
  `history-graph`, `statistics-graph`, ...) ist ein in HA eingebauter
  Kartentyp.
  - `async_regenerate_dashboard()` legt das Dashboard (Pfad `/oekofen`,
    Seitenleiste) beim ersten Aufruf an und überschreibt danach nur noch
    dessen Inhalt — durch ein `asyncio.Lock` gegen die Race zweier
    gleichzeitig setup-ender Config-Entries (zwei physische Geräte)
    abgesichert, sonst würde der zweite `async_create_item`-Aufruf
    scheitern (URL-Pfad schon vergeben).
  - Wird neu erzeugt: bei jedem Setup/Reload (nach dem ersten Coordinator-
    Refresh, siehe Architektur oben), automatisch bei jeder
    Zustandsänderung des erkannten Wartungstermin-Kalenders (`state_changed`
    getrackt), und manuell über den Dienst
    `oekofen.regenerate_dashboard`.
  - `async_build_wartung_view()` nutzt den `calendar.get_events`-Dienst
    (`return_response=True`) statt der WebSocket-API, die die alte JS
    verwendet hat — Serverseite hat keinen `hass.callWS`.
- `thermostat`-Karten zeigen `hvac_mode`/`preset_mode` **nicht** von sich
  aus direkt an — braucht explizite `features: [{type: "climate-hvac-modes"}, ...]`
  (siehe PR #37/#39).
- Temperatur-Sensoren mit stark abweichender Skala (Feuerraumtemperatur
  0-1000°C vs. alles andere 0-100°C) brauchen eigene Charts, sonst
  flacht ein `history-graph` alles andere zu einer Linie ab (siehe PR #30).

## Testing

- Sandbox hat kein Python 3.14 (das `homeassistant==2026.8.2`-Pin aus
  `requirements-test-ha.txt` braucht es). Workaround: eigenes venv mit
  Python 3.13 + `homeassistant<2026.3` (löst zu `2026.2.3` auf — nah genug,
  um echte Regressionen zu fangen, auch wenn nicht exakt der CI-Pin).
  ```
  python3.13 -m venv .venv
  source .venv/bin/activate
  pip install pytest pytest-asyncio aiohttp async-timeout "homeassistant<2026.3"
  python -m pytest tests/ -q
  ```
- `python3 -m py_compile custom_components/oekofen/*.py` für schnellen
  Syntax-Check ohne Dependencies.
- `tests/test_dashboard.py` testet `dashboard.py`s View-Bau-Funktionen pur
  (Plain-Dict-Entities + einem `SimpleNamespace`-Fake für `hass.states`),
  ohne echten `hass` — genau wie die alte JS über Node-Dry-Runs getestet
  wurde, nur jetzt als echte pytest-Suite.
- Style: `FakeCoordinator`/`make_point` aus `tests/conftest.py` statt eines
  echten `hass`/Event-Loops — die meisten Entity-Tests brauchen nur
  `coordinator.data`/`coordinator.last_update_success`.

## Versionierung

- `manifest.json`'s `"version"` ist die Quelle der Wahrheit.
  `tests/test_readme_version.py` erzwingt, dass README's
  `**Version**: X.Y.Z`-Footer und eine passende `### Version X.Y.Z`-
  Changelog-Überschrift dazu existieren — beide bei jedem Versions-Bump
  mitpflegen.
- Version bumpen bei: Breaking Changes, nutzerspürbaren Fixes. Nicht bei
  rein internem Cleanup/Tests. (Bis 0.9.8 auch bei jeder Änderung an
  `www/oekofen-strategy.js`, wegen des versions-basierten Cache-Busters —
  seit 0.10.0 entfällt das, siehe Frontend/Dashboard oben.)

## Git-Workflow dieses Projekts

- Ein einziger Arbeits-Branch (`claude/repo-analysis-1xgpe4` o.ä.) — PRs
  aus diesem Branch gegen `main`, nach Merge **immer** neu syncen bevor der
  nächste Change startet:
  ```
  git fetch origin main && git checkout -B <branch> origin/main
  ```
  (bewahrt uncommitted Änderungen, solange sie nicht mit dem neuen Main
  kollidieren). Da nur ein Branch existiert, können nicht mehrere PRs
  parallel offen sein — neue Commits landen automatisch in der noch offenen
  PR desselben Branches.
- Merge erst nach explizitem "ja, merge" vom Nutzer — dieses Projekt läuft
  live gegen eine echte Heizungsanlage.

## Bekannte, bewusst nicht behobene Punkte

- **Poll-Payload-Split** (Zeitplan-/Mail-Parameter seltener als alle 15s
  pollen): geprüft, nicht umgesetzt — Aufwand (Force-Refresh-Mechanismus
  für mehrere Schreibpfade) steht in keinem Verhältnis zum Nutzen, 15s-
  Kombi-Polling lief im Livetest sauber.
- `async_request_refresh()` nach jedem Schreibvorgang holt alle ~300
  Parameter neu (nicht nur den geschriebenen) — durch HA's Standard-
  Debouncer (10s, immediate) auf max. 2 Vollabfragen/10s gedeckelt, nicht
  dringend.
