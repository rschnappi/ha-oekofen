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
  1. `_async_register_frontend_resources(hass)` **zuerst**, vor jeglichem
     Netzwerkzugriff zum Gerät (`api.authenticate()`,
     `async_discover_circuits()`). Grund: ein Client (z.B. Kiosk-Tablet), der
     das Dashboard lädt, sobald HA/Frontend erreichbar ist — was vor dem
     Ende dieser Integration-Setup passieren kann — bekommt sonst
     `index.html` ohne das Strategy-JS-Script-Tag ausgeliefert ("Timeout
     waiting for strategy element ... to be registered"). War **keine**
     Cache-Sache, wie zuerst angenommen (siehe PR #30/#31 vs. #38).
  2. `hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` —
     jede Plattform registriert ihre Parameter.
  3. `coordinator.async_refresh()` — **nicht**
     `async_config_entry_first_refresh()`. Letzteres wirft
     `ConfigEntryNotReady` bei Fehlschlag, was HA dazu bringt,
     `async_setup_entry` (inkl. `async_forward_entry_setups`) komplett neu
     zu versuchen, ohne die Plattformen des fehlgeschlagenen Versuchs
     abzumelden → `EntityComponent` wirft `ValueError: already been setup!`
     → Integration hängt dauerhaft in `SETUP_ERROR`. `async_refresh()` loggt
     nur und setzt `last_update_success = False`, Entities zeigen dann
     korrekt "nicht verfügbar" bis zum nächsten Poll (siehe PR #32).
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

## Frontend/Dashboard (`www/oekofen-strategy.js`)

- Wird über `add_extra_js_url()` registriert, URL cache-gebustet mit einem
  Hash des tatsächlichen Datei-Inhalts als Query-Param (`?v=<hash>`), nicht
  mit `manifest.json`s Version — die wird von Hand gepflegt und wurde in
  der Praxis mehrfach hintereinander vergessen, während diese Datei sich
  weiter änderte, was einen versions-basierten Cache-Buster für jedes
  dieser Releases lautlos wirkungslos gemacht hätte (siehe PR #30/#31/#52).
- **Die Strategy-JS muss cachebar bleiben.** HA's Frontend gibt einem
  Custom-Strategy-Element nur wenige Sekunden zum Registrieren. Mit
  `no-store` (0.9.2–0.9.6) brauchte *jeder* Dashboard-Aufruf einen frischen
  Netz-Roundtrip innerhalb dieser Frist — im Desktop-Browser am LAN
  unauffällig, in einer kalt gestarteten WebView (z. B. Android-Companion-
  App) reproduzierbar zu langsam → „Timeout waiting for strategy element
  …" bei jedem Versuch (siehe PR #52). Seit 0.9.8 wird die Datei mit
  `max-age=31536000, immutable` plus inhalts-basiertem ETag/304 ausgeliefert
  — sicher, weil die URL bereits inhalts-gehasht ist und sich unter einer
  gegebenen URL nie ändert.
- `thermostat`-Karten zeigen `hvac_mode`/`preset_mode` **nicht** von sich
  aus direkt an — braucht explizite `features: [{type: "climate-hvac-modes"}, ...]`
  (siehe PR #37/#39).
- Temperatur-Sensoren mit stark abweichender Skala (Feuerraumtemperatur
  0-1000°C vs. alles andere 0-100°C) brauchen eigene Charts, sonst
  flacht ein `history-graph` alles andere zu einer Linie ab (siehe PR #30).
- Bekannter Fehler `"Timeout waiting for strategy element ... to be
  registered"` → zwei bekannte Ursachen, **beide keine reine Cache-Sache**:
  Setup-Reihenfolge (oben) und ein zu langsamer JS-Fetch innerhalb der
  Registrierungsfrist (behoben in 0.9.8, siehe oben). Nutzer nicht
  wiederholt Cache leeren lassen — das erzwingt nur den Kaltstart-Fall.

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
- `node --check custom_components/oekofen/www/oekofen-strategy.js` für die
  Dashboard-Strategy — es gibt keine JS-Testsuite dafür.
- Style: `FakeCoordinator`/`make_point` aus `tests/conftest.py` statt eines
  echten `hass`/Event-Loops — die meisten Entity-Tests brauchen nur
  `coordinator.data`/`coordinator.last_update_success`.

## Versionierung

- `manifest.json`'s `"version"` ist die Quelle der Wahrheit.
  `tests/test_readme_version.py` erzwingt, dass README's
  `**Version**: X.Y.Z`-Footer und eine passende `### Version X.Y.Z`-
  Changelog-Überschrift dazu existieren — beide bei jedem Versions-Bump
  mitpflegen.
- Version bumpen bei: JS-Änderungen (Cache-Bust!), Breaking Changes,
  nutzerspürbaren Fixes. Nicht bei rein internem Cleanup/Tests.

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
