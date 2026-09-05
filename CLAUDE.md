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

## Geräteuhrzeit (`datetime.py`'s `device_clock`)

- **Einziges Feld mit `commit_parameter`**: anders als Party-Endzeit/
  Urlaub-Start/-Ende (die nur einen zukünftigen Zeitpunkt speichern, den
  das Gerät später mit seiner eigenen laufenden Uhr vergleicht) setzt
  dieses Feld die **laufende Systemuhr des Geräts selbst** — ein
  Schreibvorgang auf `L_fernwartung_uhrzeit_neu` wird erst mit
  `L_fernwartung_setze_uhrzeit=1` im selben Request wirksam (`set_data_multi`,
  nicht `set_data`).
- **Das Gerät addiert beim Commit selbst nochmal +2h** auf den
  gesendeten Wert — bestätigt live gegen ein echtes Gerät (2026-09-05),
  sowohl über diese Integration als auch direkt über die native
  ÖkoFEN-Web-UI des Geräts (dessen eigenes Datum/Uhrzeit-Feld zeigt
  denselben +2h-Versatz zwischen Eingabe und übernommenem Wert). Das ist
  also eine Eigenheit der Geräte-Firmware selbst beim *Commit* der
  laufenden Uhr, keine Bug in `datetime_common.py`s gemeinsamer
  Umrechnung — die Lese-Seite (`device_seconds_to_datetime`, für den
  separaten `read_parameter`) und alle anderen Datetime-Felder sind
  bereits gegen ein echtes Gerät verifiziert und bleiben unangetastet.
  `async_set_value()` zieht deshalb **nur für dieses eine Feld**
  (`self._commit_parameter` gesetzt) 2 Stunden vom berechneten
  Sekundenwert ab, bevor er gesendet wird.
- **Ein einzelner Fehlversuch hat einmal die komplette Integration
  ausgesperrt**: ein falsch gesetzter Uhrzeit-Wert (Gerät landete ~4h in
  der Zukunft) führte dazu, dass jede folgende Anfrage — nicht nur an
  dieses Feld, an die **gesamte** Integration — mit `HTTP 403` abgelehnt
  wurde (alle Entities "nicht verfügbar"). Vermutung: das
  `pksession`-Cookie wird geräteseitig zeitbasiert validiert, ein
  Uhrsprung um mehrere Stunden macht die eigene, gerade noch gültige
  Session ungültig. **401 löst automatisches Reauth in
  `pellematic_api.py` aus, 403 nicht** (wird als harter Fehler
  durchgereicht) — die Integration erholt sich von diesem Zustand also
  nicht von selbst.
  - **Recovery**: `homeassistant.reload_config_entry` mit der
    `oekofen`-Config-Entry-ID (erzwingt ein komplett neues
    `PellematicAPI`-Objekt inkl. frischer `aiohttp.ClientSession`/
    Cookie-Jar → neuer Login → neues Cookie). Ein voller HA-Neustart
    wäre nicht nötig gewesen. NICHT wiederholt mit anderen Werten gegen
    das Feld schreiben in der Hoffnung, es löst sich - das verlängert im
    Zweifel nur die Downtime.
  - Die 2h-Kompensation oben ist nur an EINEM validierten Datenpunkt
    (Eingabe über diese Integration, direkt beobachtetes Ergebnis)
    kalibriert. Falls sie sich als nicht robust erweist (andere
    ÖkOfen-Firmware-Version, andere Zeitzone als Europe/Vienna, DST-Wechsel
    exakt am Schreibzeitpunkt), das Feld eher konservativ behandeln
    (z. B. nur lesend nutzen) statt den Offset blind größer zu drehen.

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
  `{"views": [...]}`-Dashboard über HAs eigene Lovelace-Storage-API —
  derselbe Mechanismus, mit dem HA selbst das Onboarding-Dashboard "Karte"
  anlegt, siehe `homeassistant/components/lovelace/__init__.py`s
  `_create_map_dashboard`. Kein Custom Element, kein Registrierungs-
  Timeout, keine JS-Datei mehr im Repo — jede verwendete Karte
  (`markdown`, `tile`, `grid`, `thermostat` mit `features`, `calendar`,
  `history-graph`, `statistics-graph`, `entities`, ...) ist ein in HA
  eingebauter Kartentyp.
  - **`hass.data["lovelace"]` ist ein `LovelaceData`-Dataclass
    (Attribut-Zugriff `.dashboards`), kein Dict** — der ursprüngliche
    0.10.0-Code ging von einem Dict mit `"dashboards"`/
    `"dashboards_collection"`-Keys aus (stimmte mit dem lokal gepinnten,
    2 Jahre alten Test-HA überein, brach aber live gegen 2026.9.0 mit
    `AttributeError: 'LovelaceData' object has no attribute 'get'`, siehe
    PR #59). **Zusätzlich hält HA-Core die für `async_create_item` nötige
    `DashboardsCollection`-Instanz nur noch als lokale Variable innerhalb
    von lovelace's eigenem `async_setup`** — über `hass.data` für andere
    Integrationen gar nicht mehr erreichbar. Lösung: `_async_create_and_
    register_dashboard()` legt eine eigene, zweite `DashboardsCollection`-
    Instanz an (zeigt auf dieselbe Storage-Datei, daher dauerhaft
    kompatibel mit dem, was HA selbst beim nächsten Neustart einliest),
    und registriert Sidebar-Panel + `dashboards[...]`-Eintrag für den
    laufenden Boot manuell nach. Payload braucht `"allow_single_word":
    True`, weil `"oekofen"` keinen Bindestrich enthält.
  - `async_regenerate_dashboard()` legt das Dashboard (Pfad `/oekofen`,
    Seitenleiste) beim ersten Aufruf an und überschreibt danach nur noch
    dessen Inhalt — durch ein `asyncio.Lock` gegen die Race zweier
    gleichzeitig setup-ender Config-Entries (zwei physische Geräte)
    abgesichert, sonst würde der zweite `async_create_item`-Aufruf
    scheitern (URL-Pfad schon vergeben). Retryt sich selbst (0.5s,
    `asyncio.create_task`), falls `hass.data["lovelace"]` bei Aufruf noch
    nicht existiert.
  - Wird neu erzeugt: bei jedem Setup/Reload (nach dem ersten Coordinator-
    Refresh, siehe Architektur oben), automatisch bei jeder
    Zustandsänderung des erkannten Wartungstermin-Kalenders (`state_changed`
    getrackt), **und automatisch sobald überhaupt ein neuer, passend
    benannter Kalender auftaucht** (`async_track_state_added_domain(hass,
    ["calendar"], ...)`, seit 0.10.2) — die Kalender-Integration kann
    innerhalb derselben Bootstrap-Stufe nach oekofen laden, ohne diesen
    zweiten Listener bliebe das Dashboard sonst permanent ohne
    Wartungs-Tab, bis der Boot-Reihenfolge-Zufall einmal anders ausfällt.
    Zusätzlich manuell über den Dienst `oekofen.regenerate_dashboard`.
  - `async_build_wartung_view()` nutzt den `calendar.get_events`-Dienst
    (`return_response=True`) statt der WebSocket-API, die die alte JS
    verwendet hat — Serverseite hat keinen `hass.callWS`. Der Service-Call
    ist in `try/except` gekapselt: `async_build_dashboard_config()` hat
    keinerlei eigenes Error-Handling um diesen Aufruf, eine unbehandelte
    Exception hier würde also die **gesamte** Dashboard-Regenerierung
    (nicht nur die Wartungs-Ansicht) abbrechen.
  - **MDI-Icon-Namen werden von HA nicht validiert** — ein nicht
    existierender Name (`mdi:calendar-wrench` war nie ein echtes Icon)
    rendert einfach gar kein Icon, statt einen Fehler zu werfen. Ergebnis:
    ein technisch vorhandener, klickbarer, aber optisch leerer Tab in der
    Tableiste, der wie ein Bug ("Tab fehlt") aussieht, aber keiner ist
    (PR #61). Bei neuen Icon-Strings im Zweifel ein garantiert
    existierendes Basis-Icon nehmen (`mdi:wrench`, `mdi:calendar`, ...).
  - **Seit 0.11.0**: Ist eine der drei `blueprints/automation/oekofen/`-
    Automatisierungen ("Anlage vor Wartungstermin ausschalten")
    konfiguriert, liest der Wartungs-Tab deren tatsächliche Blueprint-
    Inputs live aus und zeigt Automatisierungs-Status, geschaltete Entity
    und einen Szene-Wiederherstellen-Knopf plus Infokarte (Prüfzeit,
    Stichworte, Benachrichtigungsziel). Nutzt
    `homeassistant.components.automation.automations_with_blueprint()`
    (öffentliche HA-Core-Funktion, dieselbe, die die Blueprint-Seite für
    "N Automatisierungen nutzen dieses Blueprint" verwendet) zum Finden
    der Entity-IDs, greift dann aber auf `AutomationEntity._blueprint_
    inputs` zu (privates Attribut ohne öffentlichen Getter außer dem
    Blueprint-Pfad selbst über `referenced_blueprint`) — defensiv über
    `getattr`/`try-except`, kein Absturz bei fehlender/geänderter Struktur.
    **0.11.0 fand live gegen eine echte Instanz trotzdem nichts**: der
    Nutzer hatte die identische Logik von Hand als normale
    YAML-Automatisierung geschrieben, nie das eigentliche Blueprint
    importiert — `automations_with_blueprint()` findet solche Automat-
    isierungen naturgemäß nicht. Seit 0.11.1 zusätzlich Erkennung
    handgeschriebener Automatisierungen über das öffentliche
    `AutomationEntity.raw_config`-Attribut (im Gegensatz zu
    `_blueprint_inputs` für JEDE Automatisierung befüllt, nicht nur
    Blueprint-Instanzen): Muster `scene.create` → `select.select_option`
    (→ optional `notify.send_message`), rekursiv auch in
    `if/then/else`- und `choose/sequence`-verschachtelten Actions gesucht.
    Best-effort — nicht sicher extrahierbare Felder (z. B. Termin-
    Stichworte in einem frei formulierten Jinja-Template) werden
    weggelassen statt geraten.
    **Erkennung matcht nur auf den Dateinamen** (`wartung_vorbereiten.yaml`),
    nicht den vollen Blueprint-Pfad inkl. Ordner: der Ordner hängt davon ab,
    wie/wo der Nutzer die Datei abgelegt hat (dokumentierte
    `blueprints/automation/oekofen/`-Konvention, ein abweichender
    Ordnername bei URL-Import, oder - da diese Integration selbst keinen
    neuen Unterordner anlegen kann, siehe unten - flach direkt in
    `blueprints/automation/`).
  - **Diese Integration kann keine neuen Unterordner unter
    `blueprints/automation/` anlegen** - die verfügbaren Werkzeuge dafür
    setzen voraus, dass der Zielordner bereits existiert. Blueprint-Dateien
    für einen Nutzer müssen entweder in einen bereits existierenden Ordner
    oder flach direkt in `blueprints/automation/` geschrieben werden (daher
    das Dateiname-only-Matching oben statt eines festen Ordnerpfads).
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
  um die meisten Regressionen zu fangen, auch wenn nicht exakt der CI-Pin).
  ```
  python3.13 -m venv .venv
  source .venv/bin/activate
  pip install pytest pytest-asyncio aiohttp async-timeout "homeassistant<2026.3"
  python -m pytest tests/ -q
  ```
  **Vorsicht bei allem, was tief in HA-Core-Internals reingreift**
  (`dashboard.py`s Lovelace-/Automation-Introspektion): "nah genug" hat bei
  `hass.data["lovelace"]`s Struktur (Dict → `LovelaceData`-Dataclass,
  irgendwann zwischen 2024.4 und 2026.9) und bei `frontend.
  async_panel_exists` (existiert in 2026.9.0, fehlt noch in 2026.2.3) NICHT
  gereicht — beides brach erst live gegen die tatsächliche Nutzerversion,
  während die 2026.2.3-Tests weiterhin grün waren. Bei Unsicherheit: die
  exakte Nutzerversion aus dem HA-Startlog ("Starting Home Assistant
  X.Y.Z") per `curl https://raw.githubusercontent.com/home-assistant/core/
  X.Y.Z/homeassistant/components/<component>/__init__.py` gegen die echte
  getaggte Quelle prüfen, statt sich auf den lokalen Pin oder den
  `dev`-Branch (kann selbst neuer als jede Release sein) zu verlassen.
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
