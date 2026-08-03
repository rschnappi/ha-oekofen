# ÖkOfen Pellematic Home Assistant Integration

Eine custom Home Assistant Integration für ÖkOfen Pellematic Heizsysteme, die auf umfangreichen Tests und Analysen basiert.

## 🔥 Version 0.4.0 - Mit Sprachunterstützung und Services

Diese Integration bietet vollständige Kontrolle über Ihr ÖkOfen Heizsystem mit über 80 Sensoren, Services zum Ändern der Betriebsarten und mehrsprachiger Unterstützung.

## ✅ Getestete und funktionierende Konfiguration (November 2025)

### Authentifizierung (VERIFIZIERT ✓)
- **Endpoint**: `POST /index.cgi`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Parameter**: `username`, `password`, `language=de`, `submit=Anmelden`
- **Erfolg**: HTTP 303 Redirect + `Set-Cookie: pksession=XXXXX` + `LoginError=0`
- **Session**: Cookie-basiert (`pksession`)

### Datenabfrage
- **Endpoint**: `POST /?action=get&attr=1`
- **Content-Type**: `application/json`
- **Body**: JSON-Array der Parameter, z.B. `["CAPPL:LOCAL.L_aussentemperatur_ist"]`
- **Headers**: `X-Requested-With: XMLHttpRequest` erforderlich
- **Cookie**: Session-Cookie von Login muss mitgesendet werden

## 🚀 Installation

### HACS (Empfohlen)
1. HACS öffnen
2. "Custom repositories" hinzufügen
3. Repository URL: `https://github.com/rschnappi/ha-oekofen`
4. Kategorie: "Integration"
5. Repository hinzufügen und installieren
6. Home Assistant neu starten

### Manuell
1. Repository herunterladen
2. `custom_components/oekofen/` nach `<config>/custom_components/` kopieren
3. Home Assistant neu starten

## ⚙️ Konfiguration

### Über die UI (Empfohlen)
1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. "ÖkOfen" suchen und auswählen
3. Konfigurationsdaten eingeben:
   - **Host**: IP-Adresse oder Hostname Ihres ÖkOfen-Geräts (z.B. `192.168.1.100`)
   - **Benutzername**: Ihr ÖkOfen Web-Interface Benutzername
   - **Passwort**: Ihr ÖkOfen Web-Interface Passwort
   - **Sprache**: Deutsch, Englisch, Französisch oder Italienisch (Standard: Deutsch)

Die gewählte Sprache bestimmt die Sensornamen und Werte, die von der API zurückgegeben werden.

### Verbindungsdaten nachträglich ändern

Über **Einstellungen** → **Geräte & Dienste** → ÖkOfen-Integration → **Konfigurieren** lassen sich IP-Adresse, Benutzername, Passwort und Sprache jederzeit anpassen (z.B. nach einem IP-Wechsel), ohne die Integration entfernen und neu einrichten zu müssen. Nach dem Speichern wird die Integration automatisch neu geladen.

## 📊 Verfügbare Sensoren

Die Integration stellt über 80 Sensoren zur Verfügung, organisiert nach Kategorien:

### 🔧 Betriebsarten
- Anlage Betriebsart (Aus/Auto/Warmwasser)
- Heizkreis Betriebsart (Aus/Auto/Heizen/Absenken)
- Warmwasser Betriebsart (Aus/Auto/Ein)
- Pellematic Betriebsart (Aus/Auto/Ein)

### 🌡️ Allgemein
- Außentemperatur
- Software Version

### 🔥 Pellematic (Kessel)
- Kesselstatus
- Kesseltemperatur & Solltemperatur
- Abgastemperatur
- Feuerraumtemperatur & Solltemperatur
- Pelletverbrauch (heute, gestern, gesamt)
- Pelletvorrat
- Aschelade Status
- Störungsnummer & Störungsmeldung
- Betriebsstunden (gesamt, Heizen, Warmwasser)
- Starts (gesamt, erfolglos)

### 🏠 Heizkreis
- Raumtemperatur
- Vorlauftemperatur & Solltemperatur
- Heizkreispumpe Status
- Einstellungen (Raumtemp Heizen/Absenken, Heizkennlinie, Heizgrenze)
- Aktives Zeitprogramm

### 💧 Warmwasser
- Warmwassertemperatur & Solltemperatur
- Warmwasserpumpe Status
- Einstellungen (Solltemperatur, Zeitprogramm)
- Einmal Aufbereiten

### 🗄️ Puffer & Pumpen
- Puffertemperaturen (Oben, Mitte, Unten)
- Pufferpumpen Status
- Zubringerpumpe Modus & Status

## 🎚️ Steuerbare Entities (number/select/switch/datetime/time/climate)

Neben den reinen Sensoren stellt die Integration seit v0.6.0 zunehmend
**schreibbare** Standard-HA-Entities bereit, die direkt in Dashboards,
Automatisierungen und Skripten nutzbar sind - keine `input_number`/
`input_select`-Helfer mehr nötig:

- **`number.*`** – Sollwerte (Raumtemp Heizen/Absenken/Urlaub, Heizkennlinie,
  Fußpunkt, Heizgrenzen, Vorhaltezeit, Raumfühlereinfluss, Hysterese;
  Warmwasser-Solltemp/Min/Überhöhung/Nachlaufzeit/Hysterese; Pellematic
  Regel-/Abschalttemperatur, Abgastemp-Minimum, Leistungsstufe)
- **`select.*`** – Betriebsarten (Anlage/Heizkreis/Warmwasser/Pellematic),
  aktives Zeitprogramm, Warmwasser-Vorrang & Legionellenschutz
- **`switch.*`** – Party-/Urlaubsprogramm, Warmwasser "Einmal Aufbereiten",
  sowie je ein Schalter pro Wochentag und Zeitprogramm-Block
  (`<kreis>_zeit_<1|2>_<wochentag>_aktiv`)
- **`datetime.*`** – Party-Endzeit, Urlaub-Start/-Ende
- **`time.*`** – Von-/Bis-Uhrzeiten der Zeitprogramme (3 Blöcke × 7 Tage ×
  2 Zeitprogramme × Heizkreis/Warmwasser)
- **`climate.*`** *(neu in v0.8.0)* – Ein Climate-Entity pro Heizkreis und
  pro Warmwasser-Kreis, kompatibel mit HA's Standard-Thermostat-Karte:
  - Heizkreis: `off` / `auto` / `heat`, plus Preset **"Absenken"**
  - Warmwasser: `off` / `auto` / `heat` (kein Preset, da keine
    Absenken-Stufe am Gerät vorhanden ist)

  Ist-/Solltemperatur und Min/Max stammen aus denselben Parametern wie die
  zugehörigen `sensor.*`/`number.*`-Entities - keine doppelte Datenquelle.

## 🎛️ Services

Die Integration bietet folgende Services zum Steuern des Heizsystems:

⚠️ **Legacy-Hinweis**: `set_system_mode`/`set_heating_mode`/`set_hot_water_mode`/`set_pellematic_mode` steuern dieselben Parameter, die inzwischen über die nativen `select.*`/`climate.*`-Entities (Betriebsart-Dropdown bzw. Thermostat-Karte) komfortabler mit Status-Feedback verfügbar sind. Die Services bleiben aus Kompatibilitätsgründen bestehen, für **neue** Automatisierungen aber bitte die Entities bevorzugen. `oekofen.set_parameter` bleibt weiterhin der generische Weg für alle Parameter, die (noch) keine eigene Entity haben.

### `oekofen.set_system_mode`
Setzt den Betriebsmodus der Anlage.
```yaml
service: oekofen.set_system_mode
data:
  mode: auto  # aus, auto, warmwasser
```

### `oekofen.set_heating_mode`
Setzt den Betriebsmodus eines Heizkreises.
```yaml
service: oekofen.set_heating_mode
data:
  circuit: 0  # 0-5
  mode: auto  # aus, auto, heizen, absenken
```

### `oekofen.set_hot_water_mode`
Setzt den Betriebsmodus für Warmwasser.
```yaml
service: oekofen.set_hot_water_mode
data:
  circuit: 0  # 0-2
  mode: auto  # aus, auto, ein
```

### `oekofen.set_pellematic_mode`
Setzt den Betriebsmodus des Pellematic Kessels.
```yaml
service: oekofen.set_pellematic_mode
data:
  unit: 0  # 0-3
  mode: auto  # aus, auto, ein
```

### `oekofen.set_parameter`
Setzt einen rohen Parameter-Wert (für Experten).
```yaml
service: oekofen.set_parameter
data:
  parameter: "CAPPL:LOCAL.hk[0].raumtemp_heizen"
  value: 20.0
  divisor: 10  # optional
```

## 📱 Dashboard

Ein vorgefertigtes Dashboard ist verfügbar in [`dashboard_example.yaml`](dashboard_example.yaml).

⚠️ **Wichtig zu den Entity-IDs**: Diese Integration übernimmt Sensor-Namen direkt vom Gerät (in der Sprache, die du beim Einrichten gewählt hast), und Home Assistant leitet die Entity-ID daraus automatisch ab. Die tatsächlichen Entity-IDs sind deshalb **nicht** vorhersagbar (z.B. `sensor.okofen_192_168_1_50_betriebsart` statt eines festen Namens) und hängen von deinem Host, deiner Gerätesprache und ggf. dem zugewiesenen Bereich (Area) ab. Suche unter **Einstellungen → Geräte & Dienste → Entitäten** nach "okofen", um deine echten Entity-IDs zu finden, und ersetze den Platzhalter `DEINHOST` in der YAML-Datei entsprechend. Die neueren `number.*`/`select.*`/`switch.*`/`datetime.*`/`time.*`/`climate.*`-Entities sind dagegen **namensbasiert** (z.B. `climate.heizraum_okofen_pellematic_heizkreis_1`), nicht host-abhängig.

### Installation des Dashboards
1. Gehen Sie zu **Einstellungen** → **Dashboards**
2. Klicken Sie auf **+ Dashboard hinzufügen**
3. Wählen Sie **Neue Ansicht aus YAML erstellen**
4. Kopieren Sie den Inhalt aus `dashboard_example.yaml` und ersetzen Sie `DEINHOST` durch Ihre echten Entity-IDs
5. Das Dashboard zeigt (Kacheln-Layout, 2 pro Reihe für lesbare Beschriftungen):
   - **Übersicht**: Betriebsarten (als Dropdown-Kacheln), wichtigste Sensoren, Party/Urlaub-Kurzstatus
   - **Pellematic**: Kessel, Einstellungen (Sollwerte editierbar), Pellets, Störungen
   - **Heizkreis**: `thermostat`-Karte (Aus/Auto/Heizen + Preset "Absenken") oben, darunter Einstellungen und Party/Urlaub
   - **Warmwasser**: `thermostat`-Karte (Aus/Auto/Ein) oben, darunter Einstellungen
   - **Puffer & Pumpen**: Pufferspeicher und Pumpen (Pumpen-Zuordnung ist eine Vermutung, siehe Hinweis im Dashboard)
   - **Statistik**: Betriebsstunden, Verlaufs- und Langzeitgraphen
   - **Zeitprogramme**: Wochentage als antippbare Kacheln je Zeitprogramm, Von-/Bis-Zeiten als Liste (Block 1; Block 2/3 sind bei Bedarf leicht ergänzbar)

### Werte direkt im Dashboard verändern

Seit v0.6.0/v0.8.0 liefert die Integration native, direkt editierbare `number.*`/`select.*`/`switch.*`/`datetime.*`/`time.*`/`climate.*`/`text.*`-Entities für praktisch alle Sollwerte (Raumtemperatur, Vorlauf Max/Min, Heizkurve, Warmwassertemperatur, Zeitprogramm-Auswahl, Zeitprogramm-Zeiten und -Wochentage, Party-/Urlaubsprogramm, Betriebsarten als Thermostat-Karte, Mail/SMTP-Einstellungen, …). Ein Umweg über `input_number`/`input_select`-Helfer ist dafür **nicht mehr nötig** – es gibt inzwischen keine bekannten Lücken mehr, `helpers_example.yaml`/`automations_example.yaml` wurden entfernt.

**Achtung** bei allen schreibbaren Entities gleichermaßen: Sie greifen unmittelbar in den laufenden Heizungsbetrieb ein – nach Änderungen zunächst mit einem unkritischen Wert testen.

### ⚠️ Installateur-Ebene-Felder

Ein Teil der Sollwerte ist am Original-Gerät selbst **hinter dem Installateur-/Techniker-Code** (`main.codeebene`) versteckt – am Touchdisplay bzw. in der Geräte-Weboberfläche kommt man ohne diesen Code gar nicht an sie heran. Diese Integration liest das Gerät über dieselbe API an, die auch die Weboberfläche nutzt, und kann diese Werte deshalb technisch trotzdem schreiben. Sie sind bewusst **nicht** auf reinen Lesezugriff beschränkt (falls du sie doch mal brauchst), aber in Name (Präfix "⚠️") und Icon markiert und tragen ein `warnhinweis`-Attribut (sichtbar in Entwicklertools → Zustand bzw. im Mehr-Info-Dialog der Entity):

- Heizkreis: Vorlauf Max, Vorlauf Min
- Warmwasser: Vorrang, Überhöhung, Nachlaufzeit, Einschalthysterese, Legionellenschutz
- Pellematic: Regeltemperatur (klassisch + Smart), Abschalttemperatur, Abgastemp-Minimum, Leistungsstufe (klassisch + Smart)

**Falsche Werte hier können die Anlage beschädigen oder Sicherheitsfunktionen beeinträchtigen** (insbesondere Kessel-Abschalttemperatur und Abgastemp-Minimum sind vermutlich Schutzparameter, keine reinen Komfort-Einstellungen). Im Zweifel am Gerät selbst mit Installateur-Code ändern, oder Rücksprache mit dem Installateur halten.

### ℹ️ Betriebsart bei Anlage "Aus"

Am Original-Gerät ist die Heizkreis-/Warmwasser-Betriebsart (`select.*_betriebsart`, sowie die Modus-Auswahl der zugehörigen `climate.*`-Entity) ausgegraut, solange die **Anlage-Betriebsart auf "Aus" steht** – eine reine UI-Ausgrauung am Gerät, kein Sicherheitsmechanismus. Diese Integration lässt das Feld deshalb weiterhin editierbar, zeigt in diesem Zustand aber ein `hinweis`-Attribut: Änderungen wirken sich erst aus, sobald die Anlage wieder auf Auto/Warmwasser gestellt wird.

### Langzeitstatistik

Sensoren mit numerischem Wert haben bereits die passende `state_class` (measurement bzw. total_increasing), wodurch Home Assistant automatisch **Langzeitstatistiken** führt (im Gegensatz zur normalen Historie verfallen diese nicht nach ein paar Tagen). Für echte Langzeit-Trends (z.B. Temperaturverlauf über Monate, oder Brennerstarts pro Tag zur Kurztakt-Analyse) nutzt `dashboard_example.yaml` dafür `statistics-graph`-Karten statt `history-graph`.

⚠️ **Wichtig bei einem Update von Version < 0.4.0**: Diese Version hat das `unique_id`-Schema der Sensoren geändert (siehe Changelog), wodurch sich auch die Entity-IDs ändern. Das **unterbricht die Kontinuität bereits gesammelter Langzeitstatistiken** – die alten Sensoren behalten ihre Historie, werden aber nicht mehr aktualisiert; die neuen Sensoren starten bei null. Um die Historie zu erhalten, kannst du nach dem Update die alte, verwaiste Entity löschen und die neue Entity in **Einstellungen → Entitäten → [Entity] → Einstellungen → Entity-ID** auf die alte ID umbenennen – Home Assistant führt die Statistik dann unter derselben Statistik-ID (die am Entity-ID-String hängt) nahtlos weiter.

## 🔧 Erweiterte Konfiguration

### Update-Intervall
Standardmäßig werden Daten alle 30 Sekunden abgerufen. Dies kann in der Sensor-Konfiguration angepasst werden.

### Debug-Modus
Für erweiterte Diagnose können Sie das Log-Level erhöhen:

```yaml
logger:
  default: warning
  logs:
    custom_components.oekofen: debug
```

## 🔍 Fehlerbehebung

### Häufige Probleme

#### Authentifizierung fehlgeschlagen
- Überprüfen Sie Benutzername und Passwort
- Stellen Sie sicher, dass das Web-Interface des ÖkOfen-Geräts erreichbar ist
- Testen Sie die Anmeldung direkt über den Browser

#### Keine Daten erhalten
- Überprüfen Sie die Netzwerkverbindung zum ÖkOfen-Gerät
- Kontrollieren Sie die Firewall-Einstellungen
- Prüfen Sie die Home Assistant Logs auf Fehlermeldungen

#### Verbindungsfehler
```bash
# Test der Verbindung via curl
curl -X POST "http://IHR_OEKOFEN_IP/index.cgi" \
  -H "Content-Type: application/json" \
  -d '{"user":"IHR_USERNAME","pass":"IHR_PASSWORD","submit":"Anmelden"}'
```

### Debug-Informationen sammeln

Aktivieren Sie Debug-Logging und überprüfen Sie die Logs:

```yaml
logger:
  logs:
    custom_components.oekofen: debug
    custom_components.oekofen.pellematic_api: debug
```

## 🛠️ Entwicklung

### Tests

Es gibt automatisierte Tests für `pellematic_api.py` (Login, Session-Handling, Re-Authentifizierung), die bei jedem Push/PR per GitHub Actions laufen. Lokal ausführen:

```bash
pip install -r requirements-test.txt
pytest tests/ -v
```

Die Tests brauchen kein Home Assistant und keine echte Verbindung zum Gerät (HTTP wird mit `aioresponses` gemockt).

### Getestete Konfiguration
- **ÖkOfen Pellematic 2012** - Vollständig getestet
- **Home Assistant 2024.x** - Kompatibel
- **aiohttp >= 3.8.0** - Erforderlich

### API-Endpoints (Dokumentiert und getestet)
```python
# Anmeldung
POST /index.cgi
Content-Type: application/json
{"user": "username", "pass": "password", "submit": "Anmelden"}

# Datenabfrage
POST /?action=get&attr=1  
Content-Type: application/json
["CAPPL:LOCAL.L_aussentemperatur_ist", "CAPPL:FA[0].L_kesseltemperatur"]
```

### Bewährte Parameter
Die Integration verwendet nur getestete und funktionierende Parameter:
- `CAPPL:LOCAL.L_aussentemperatur_ist` - Außentemperatur ✅
- `CAPPL:FA[0].L_kesseltemperatur` - Kesseltemperatur ✅
- `CAPPL:FA[0].L_kesselstatus` - Kesselstatus ✅

## 📝 Changelog

### Version 0.8.0

- ⚙️ **Verbindungsdaten nachträglich editierbar**: Neuer Options-Flow
  (Integration → "Konfigurieren") erlaubt das Ändern von IP-Adresse,
  Benutzername, Passwort und Sprache, ohne die Integration neu einrichten
  zu müssen.
- ℹ️ `select.*_betriebsart`/`climate.*` von Heizkreis/Warmwasser zeigen jetzt
  ein `hinweis`-Attribut, solange Anlage-Betriebsart "Aus" ist (Änderungen
  wirken sich erst nach Umschalten auf Auto/Warmwasser aus - analog zum
  ausgegrauten Feld am Original-Gerät).
- ✅ Weitere native Felder ergänzt: Zirkulationspumpe Betriebsart
  (`select.*`, nicht installateurgesperrt) sowie Pellematic Regeltemperatur
  für "Smart"-Firmware (`number.*`, `frischwasser_soll_temp` - analog zum
  bestehenden Leistungsstufe-Muster, gilt je nach Firmware nur eine der
  beiden Regeltemperatur-Entities).
- 🐛 **Kritischer Fix: Heizkreis-/Warmwasser-Betriebsart las/schrieb den
  falschen Wert, sobald die Anlage nicht auf "Aus" stand.** Das Gerät
  speichert `betriebsart` pro Heizkreis/Warmwasser als 3er-Array
  (`betriebsart[0..2]`) - ein Slot pro möglicher Anlage-Betriebsart
  (Aus/Auto/Warmwasser), von denen nur der zum aktuellen Anlage-Modus
  passende Slot tatsächlich aktiv ist (siehe Original-Firmware,
  `config.min.js`). `climate.*`/`select.*` (und die Legacy-Services
  `set_heating_mode`/`set_hot_water_mode`) haben bisher immer fix
  `betriebsart[0]` verwendet - bei laufendem Anlage-Modus "Auto" (der
  Normalfall) wurde damit ein veralteter, inaktiver Slot angezeigt und
  Änderungen gingen ins Leere. Neues `betriebsart.py` löst den aktiven
  Slot jetzt live anhand von `CAPPL:LOCAL.anlage_betriebsart` auf.
- ✅ **Climate-Plattform** (`climate.py`, neu): Heizkreis und Warmwasser
  bekommen echte `climate.*`-Entities für Thermostat-Karten in HA, statt nur
  Sensoren/Number-Feldern. Mode-Mapping ist pro Kreistyp konfigurierbar
  (`mode_map`), da Heizkreis und Warmwasser unterschiedliche Betriebsarten
  am Gerät haben:
  - **Heizkreis:** Aus → `off`, Auto → `auto`, Heizen → `heat`,
    Absenken → `heat` + Preset "Absenken" (kein HA-Standardmodus, daher als
    Preset statt als eigener hvac_mode).
  - **Warmwasser:** Aus → `off`, Auto → `auto`, Ein → `heat` (kein Preset,
    dieser Kreis hat keine Absenken-Stufe am Gerät).
  - Ist-/Solltemperatur und Min/Max-Grenzen kommen aus denselben
    CAPPL-Parametern wie die bestehenden Sensor-/Number-Entities für den
    jeweiligen Kreis - keine Doppelquelle für dieselben Werte.
- 🐛 Korrektur: Preset heißt jetzt wörtlich **"Absenken"** statt des
  irreführenden generischen HA-Begriffs "Eco".

### Version 0.6.2 – 0.6.3

- 🐛 **`sensor.py`**: Sensoren mit numerischer `state_class`/`unit`
  (z. B. Pelletsfüllstand) crashten, wenn das Gerät statt einer Zahl einen
  Text wie `" leer"` lieferte. `state_class`, `device_class` **und**
  `native_unit_of_measurement` werden jetzt dynamisch unterdrückt, sobald
  der aktuelle Wert nicht numerisch ist - der Sensor zeigt den Text dann
  einfach an, statt die Entity-Registrierung zum Absturz zu bringen.
- ℹ️ Ein Versuch, ein Thermostat-Widget über die Core-`template:`-Integration
  abzubilden, wurde wieder verworfen: HA unterstützt dort **keine**
  Climate-Entities (weder alte noch neue Syntax) - siehe stattdessen
  Version 0.8.0 für die native Lösung direkt in dieser Integration.

### Version 0.6.1

- ✅ **Warmwasser "Einmal Aufbereiten"** ist jetzt ein Schalter
  (`switch.<warmwasser>_einmal_aufbereiten`) statt nur ein Lese-Sensor -
  löst einen einmaligen Warmwasser-Aufbereitungszyklus aus, analog zu
  Party-/Urlaubsprogramm.

### Version 0.6.0

- ✅ **Party- und Urlaubsprogramm** pro Heizkreis als native Entities:
  `switch.<heizkreis>_partyprogramm`, `datetime.<heizkreis>_party_endzeit`,
  `switch.<heizkreis>_urlaubsprogramm`, `number.<heizkreis>_raumtemp_urlaub`,
  `datetime.<heizkreis>_urlaub_start`, `datetime.<heizkreis>_urlaub_ende`.
  Neue `datetime`-Plattform (`datetime.py` + `datetime_common.py`) rechnet
  zwischen dem gerätespezifischen Zeitstempelformat (lokale Uhrzeit,
  gespeichert als wäre sie UTC) und HA's zeitzonenbewussten Datetimes um.
- ✅ **Warmwasser** zusätzlich editierbar: Überhöhung, Nachlaufzeit,
  Einschalthysterese (`number.*`), Vorrang und Legionellenschutz (`select.*`).
- ✅ **Pellematic** zusätzlich editierbar: Regeltemperatur, Abschalttemperatur,
  Abgastemp-Minimum, Leistungsstufe (klassisch & Smart) (`number.*`).
- ✅ **Heizkreis** zusätzlich editierbar: Raumtemperatur Urlaub (`number.*`).
- 🧹 Alle neuen Entities sind namensbasiert (nicht host-abhängig) und
  benötigen keine `input_number`/`input_select`-Helfer mehr - die
  entsprechenden Abschnitte in `dashboard_example.yaml` wurden auf die
  nativen Entities umgestellt. `helpers_example.yaml`/`automations_example.yaml`
  bleiben nur noch für Felder relevant, die (noch) nicht nativ abgedeckt sind.

### Version 0.4.0
- ⚠️ **Breaking**: `unique_id` der Sensoren ist jetzt pro Config-Entry eindeutig (`<entry_id>_<sensor_key>` statt `oekofen_<sensor_key>`), damit mehrere ÖkOfen-Geräte in derselben Home-Assistant-Instanz nicht kollidieren. Nach dem Update legt Home Assistant die Entities neu an; alte, verwaiste Entities können unter **Einstellungen → Geräte & Dienste → Entitäten** entfernt werden, falls nötig.
- ✅ Geräte-Identität (Device Registry) verwendet jetzt die stabile Config-Entry-ID statt der Host/IP-Adresse, damit ein IP-Wechsel keinen doppelten Geräteeintrag mehr erzeugt.
- ✅ Login gegen Race Conditions abgesichert: gleichzeitige Anfragen (Polling + Service-Aufruf) lösen bei abgelaufener Session nicht mehr mehrere parallele Logins aus.
- ✅ Robustere Erkennung abgelaufener Sessions: Antwortet das Gerät mit HTTP 200 und der Login-Seite (HTML) statt JSON, wird das jetzt wie eine abgelaufene Session behandelt (automatische Re-Authentifizierung) statt mit einem Fehler abzubrechen.
- 🧹 Unfertige/kaputte `dashboard_generator.py`-Skripte entfernt.

### Version 0.0.1 (Neubeginn)
- ✅ Komplette Neuentwicklung basierend auf gewonnenen Erkenntnissen
- ✅ Korrekte Content-Type: application/json Header implementiert
- ✅ Bewährte Authentifizierung via index.cgi
- ✅ Getestete Parameter und Endpoints
- ✅ Robuste Session-Verwaltung
- ✅ Config Flow für einfache Einrichtung
- ✅ Umfassende Dokumentation

## 🤝 Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.

## 🙏 Danksagungen

- **ÖkOfen** für die Pellematic-Systeme
- **Home Assistant Community** für Unterstützung und Feedback
- **Alle Tester** die bei der Entwicklung geholfen haben

## ⚠️ Haftungsausschluss

Diese Integration ist ein inoffizielles Projekt und steht in keiner Verbindung zu ÖkOfen. Verwenden Sie sie auf eigenes Risiko.

---

**Version**: 0.4.0  
**Letzte Aktualisierung**: November 2025  
**Status**: Stabil - Basierend auf umfangreichen Tests