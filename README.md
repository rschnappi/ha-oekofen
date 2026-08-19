# ÖkOfen Pellematic Home Assistant Integration

Eine Custom Home Assistant Integration für ÖkOfen Pellematic Heizsysteme (Kessel, Heizkreise, Warmwasser, Pufferspeicher, Zirkulationspumpen). Liest über 80 Werte aus und stellt praktisch alle Sollwerte des Geräts als native, direkt editierbare Home-Assistant-Entities bereit (`number`/`select`/`switch`/`climate`/`time`/`datetime`/`text`) - kein Umweg über `input_number`/`input_select`-Helfer nötig. Dazu gibt es ein fertiges, automatisch generiertes Dashboard (siehe Abschnitt "📱 Dashboard" weiter unten).

Basiert auf umfangreichen Tests gegen ein echtes Gerät sowie einer Analyse der Original-JS-Weboberfläche (`app.min.js`/`config.min.js`), um Verhalten nachzubilden, das die rohe API nicht dokumentiert (z.B. installateur-gesperrte Felder, die Slot-Struktur der Heizkreis-Betriebsart).

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

Über **Einstellungen** → **Geräte & Dienste** → ÖkOfen-Integration → **Konfigurieren** lassen sich IP-Adresse, Benutzername, Passwort und Sprache jederzeit anpassen (z.B. nach einem IP-Wechsel), ohne die Integration entfernen und neu einrichten zu müssen. Nach dem Speichern wird die Integration automatisch neu geladen. Zum Entfernen der Integration weiterhin das Drei-Punkte-Menü des Eintrags verwenden (eigene Option dafür im Konfigurieren-Dialog wurde nach einem Vorfall mit fehlerhaft dargestellten, unbeschrifteten Menüzeilen wieder entfernt - siehe Changelog).

## 📊 Verfügbare Sensoren

Über 80 Sensoren, organisiert nach Kategorien:

### 🔧 Betriebsarten
- Anlage Betriebsart (Aus/Auto/Warmwasser)
- Heizkreis Betriebsart (Aus/Auto/Heizen/Absenken)
- Warmwasser Betriebsart (Aus/Auto/Ein)
- Pellematic Betriebsart (Aus/Auto/Ein)

### 🌡️ Allgemein
- Außentemperatur
- Software Version
- Fernwartungscode 1/2 (diagnostisch)

### 🔥 Pellematic (Kessel)
- Kesselstatus
- Kesseltemperatur & Solltemperatur
- Abgastemperatur
- Feuerraumtemperatur & Solltemperatur
- Pelletverbrauch (heute, gestern, gesamt)
- Pelletvorrat
- Aschelade Status
- Störungsnummer & Störungsmeldung (löst zusätzlich eine `persistent_notification` aus, wenn das Störmelderelais auslöst)
- Betriebsstunden (gesamt, Heizen, Warmwasser)
- Starts (gesamt, erfolglos)
- Glühstab-Zündzeit (Diagnose, mit konfigurierbarer Warnschwelle als `number.*`, überlebt HA-Neustarts)

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

## 🎚️ Steuerbare Entities (number/select/switch/datetime/time/climate/text)

Neben den reinen Sensoren stellt die Integration seit v0.6.0 zunehmend
**schreibbare** Standard-HA-Entities bereit, die direkt in Dashboards,
Automatisierungen und Skripten nutzbar sind - keine `input_number`/
`input_select`-Helfer mehr nötig:

- **`number.*`** – Sollwerte (Raumtemp Heizen/Absenken/Urlaub, Heizkennlinie,
  Fußpunkt, Heizgrenzen, Vorhaltezeit, Raumfühlereinfluss, Hysterese;
  Warmwasser-Solltemp/Min/Überhöhung/Nachlaufzeit/Hysterese; Pellematic
  Regel-/Abschalttemperatur (klassisch + Smart-Firmware), Abgastemp-Minimum,
  Leistungsstufe (klassisch + Smart); Zirkulationspumpe Abschalttemperatur/
  Hysterese; Glühstab-Warnschwelle)
- **`select.*`** – Betriebsarten (Anlage/Heizkreis/Warmwasser/Pellematic/
  Zirkulationspumpe), aktives Zeitprogramm, Warmwasser-Vorrang &
  Legionellenschutz
- **`switch.*`** – Party-/Urlaubsprogramm, Warmwasser "Einmal Aufbereiten",
  Testmail senden, sowie je ein Schalter pro Wochentag und Zeitprogramm-Block
  (`<kreis>_zeit_<1|2>_<wochentag>_aktiv`)
- **`datetime.*`** – Geräteuhrzeit, Party-Endzeit, Urlaub-Start/-Ende
- **`time.*`** – Von-/Bis-Uhrzeiten der Zeitprogramme (3 Blöcke × 7 Tage ×
  2 Zeitprogramme × Heizkreis/Warmwasser/Zirkulationspumpe)
- **`text.*`** – Mail/SMTP-Einstellungen für die Fernwartung
  (Anlagenbezeichnung, SMTP-Server/-Benutzer/-Passwort, bis zu 5 Empfänger)
- **`climate.*`** – Ein Climate-Entity pro Heizkreis, Warmwasser- und
  Pellematic-Kreis, kompatibel mit HA's Standard-Thermostat-Karte:
  - Heizkreis: `off` / `auto` / `heat`, plus Preset **"Absenken"**
  - Warmwasser: `off` / `auto` / `heat` (kein Preset, da keine
    Absenken-Stufe am Gerät vorhanden ist), plus Preset **"Boost"** für
    "Einmal Aufbereiten" (zusätzlich zum eigenständigen `switch.*`)
  - Pellematic: `off` / `auto` / `heat`, gleiches Modell wie Warmwasser

  Ist-/Solltemperatur und Min/Max stammen aus denselben Parametern wie die
  zugehörigen `sensor.*`/`number.*`-Entities - keine doppelte Datenquelle.

⚠️ Ein Teil dieser Felder ist am Original-Gerät hinter dem Installateur-Code
versteckt und entsprechend markiert - siehe Abschnitt "⚠️ Installateur-Ebene-Felder"
weiter unten.

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

Zwei Wege zu einem fertigen Dashboard - für die meisten reicht **Option A**.

### Option A: Dashboard-Strategy (empfohlen)

Die Integration bringt eine eigene [Lovelace-Dashboard-Strategy](https://www.home-assistant.io/dashboards/strategies/) mit (`custom_components/oekofen/www/oekofen-strategy.js`), die das komplette Dashboard **automatisch aus den tatsächlich vorhandenen Entities generiert** - kein Suchen-und-Ersetzen von Platzhaltern, keine manuelle Pflege bei mehreren Heizkreisen. Kein manuelles Eintragen unter **Einstellungen → Dashboards → Ressourcen** nötig, die Integration registriert die Ressource beim Start selbst.

**So richtest du es ein:**
1. **Einstellungen → Dashboards → + Dashboard hinzufügen**
2. **Neue Ansicht aus YAML erstellen**
3. Den Beispiel-Inhalt der neuen Ansicht komplett löschen und stattdessen einfügen:
   ```yaml
   strategy:
     type: custom:oekofen-strategy
   ```
4. Speichern - das Dashboard baut sich jetzt automatisch auf.

Bei **mehreren ÖkOfen-Geräten** in derselben HA-Instanz werden die Ansichten aller Geräte automatisch mit Gerätename präfixiert (Titel und URL-Pfad), du musst nichts weiter tun. Um die Strategy stattdessen auf ein einzelnes Gerät zu beschränken, dessen Geräte-ID angeben (**Einstellungen → Geräte & Dienste → Gerät auswählen → die ID steht in der URL**):
```yaml
strategy:
  type: custom:oekofen-strategy
  device_id: <geraete-id>
```

**Was die Strategy generiert** (pro Gerät, automatisch angepasst an die vorhandene Hardware):
- **Übersicht**: Betriebsarten aller Kreise als Kacheln, plus alles, was keinem Kreis zugeordnet werden konnte (z.B. Anlage-Betriebsart, weitere Schalter/Datum-Zeit-Felder)
- **Puffer & Pumpen** *(nur wenn vorhanden)*: Puffertemperatur-Fühler und Umwälz-/Zirkulationspumpen-Sensoren
- **Je eine Ansicht pro Kreis** - Heizkreis 1, 2, ...; Warmwasser 1, ...; Pellematic 1, ...; Zirkulationspumpe 1, ... (nur was am Gerät wirklich existiert):
  - `thermostat`-Karte (bei Heizkreis/Warmwasser/Pellematic)
  - Schnellzugriff auf Betriebsart/Zeitprogramm
  - Einstellungen-Kachelraster (alle `number.*`/`select.*` des Kreises)
  - Eigener **⚠️ Installateur-Ebene**-Bereich für installateur-gesperrte Felder dieses Kreises, mit dem Warnhinweis als Überschrift
  - Party/Urlaub-Karte (Heizkreis) bzw. Einmal-Aufbereiten/Vorrang/Legionellenschutz (Warmwasser), falls vorhanden
  - Vollständiger Zeitprogramm-Bereich: Wochentage als antippbare Kacheln je Zeitprogramm (Zeit 1/2), Von-/Bis-Uhrzeiten für **alle 3 Zeitblöcke** als Liste
- **Statistik**: Verlaufs- und Langzeitstatistik-Karten, automatisch anhand `device_class`/`state_class`/Einheit der Sensoren zusammengestellt (Temperaturverläufe, Betriebsstunden/Ereignisse pro Tag) - nicht anhand fester Entity-Namen, funktioniert also auch bei künftig hinzukommenden Sensoren
- **Diagnose**: alle übrig gebliebenen `sensor.*`-Entities als Liste
- **Mail / SMTP**: alle `text.*`-Entities (Fernwartungs-Mailkonfiguration) als Liste

### Option B: Statische YAML-Vorlage

Ein handkuratiertes Beispiel-Dashboard liegt in [`dashboard_example.yaml`](dashboard_example.yaml) - feste Icons/Anordnung, deckt aber nur Heizkreis 1/Warmwasser 1 sowie Zeitblock 1 exemplarisch ab (weitere Kreise/Blöcke müssen manuell dupliziert werden). Sinnvoll als Ausgangspunkt für individuelle Anpassungen, für die die generierte Strategy zu starr ist.

⚠️ **Wichtig zu den Entity-IDs** (nur für Option B relevant - die Strategy aus Option A erkennt Entities zur Laufzeit und braucht das nicht): Home Assistant leitet die Entity-ID aus dem Bereich (Area) und dem Gerätenamen ab, den das Gerät zum Zeitpunkt der ersten Registrierung trägt (Standard: "ÖkOfen \<IP\>", falls du es nicht umbenannt hast) – **nicht** aus Host/IP direkt. Die tatsächlichen Entity-IDs sind deshalb **nicht** vorhersagbar (z.B. `select.heizraum_ofen_anlage_betriebsart`, wenn dein Gerät im Bereich "Heizraum" liegt und auf "Ofen" umbenannt wurde) und hängen von deiner Bereichszuordnung und dem gewählten Gerätenamen ab. Ein paar sehr alte `sensor.*`-Entities aus Zeiten vor v0.6.0 können bei dir noch rein host-basierte IDs haben (z.B. `sensor.okofen_192_168_1_50_betriebsart`), falls du seither nie neu eingerichtet hast. Suche unter **Einstellungen → Geräte & Dienste → Entitäten** nach "okofen"/deinem Gerätenamen, um deine echten Entity-IDs zu finden, und ersetze den Platzhalter `PRAEFIX` in der YAML-Datei entsprechend.

**Installation:**
1. Gehen Sie zu **Einstellungen** → **Dashboards**
2. Klicken Sie auf **+ Dashboard hinzufügen**
3. Wählen Sie **Neue Ansicht aus YAML erstellen**
4. Kopieren Sie den Inhalt aus `dashboard_example.yaml` und ersetzen Sie `PRAEFIX` durch Ihre echten Entity-IDs
5. Das Dashboard zeigt (Kacheln-Layout, 2 pro Reihe für lesbare Beschriftungen):
   - **Übersicht**: Betriebsarten (als Dropdown-Kacheln), wichtigste Sensoren, Fernwartungscodes, Party/Urlaub-Kurzstatus
   - **Pellematic**: `thermostat`-Karte oben, darunter Kessel-Sensorik, Einstellungen (Sollwerte editierbar), Pellet-System & Förderung, Störungen
   - **Heizkreis**: `thermostat`-Karte (Aus/Auto/Heizen + Preset "Absenken") oben, darunter Einstellungen und Party/Urlaub
   - **Warmwasser**: `thermostat`-Karte oben, darunter Einstellungen
   - **Puffer & Pumpen**: Pufferspeicher und Pumpen (Pumpen-Zuordnung ist eine Vermutung, siehe Hinweis im Dashboard)
   - **Statistik**: Betriebsstunden, Verlaufs- und Langzeitgraphen
   - **Zeitprogramme**: Wochentage als antippbare Kacheln je Zeitprogramm, Von-/Bis-Zeiten als Liste (Zeit 1/2, Block 1; weitere Blöcke/Zeitprogramme sind bei Bedarf leicht ergänzbar)
   - **Einstellungen**: Geräteuhrzeit, Mail/SMTP, Fernwartung, Diagnose (Glühstab-Zündzeit, Störmelderelais)

### Werte direkt im Dashboard verändern

Seit v0.6.0/v0.8.0 liefert die Integration native, direkt editierbare `number.*`/`select.*`/`switch.*`/`datetime.*`/`time.*`/`climate.*`/`text.*`-Entities für praktisch alle Sollwerte (Raumtemperatur, Vorlauf Max/Min, Heizkurve, Warmwassertemperatur, Zeitprogramm-Auswahl, Zeitprogramm-Zeiten und -Wochentage, Party-/Urlaubsprogramm, Betriebsarten als Thermostat-Karte, Mail/SMTP-Einstellungen, …). Ein Umweg über `input_number`/`input_select`-Helfer ist dafür **nicht mehr nötig**.

**Achtung** bei allen schreibbaren Entities gleichermaßen: Sie greifen unmittelbar in den laufenden Heizungsbetrieb ein – nach Änderungen zunächst mit einem unkritischen Wert testen.

### ⚠️ Installateur-Ebene-Felder

Ein Teil der Sollwerte ist am Original-Gerät selbst **hinter dem Installateur-/Techniker-Code** (`main.codeebene`) versteckt – am Touchdisplay bzw. in der Geräte-Weboberfläche kommt man ohne diesen Code gar nicht an sie heran. Diese Integration liest das Gerät über dieselbe API an, die auch die Weboberfläche nutzt, und kann diese Werte deshalb technisch trotzdem schreiben. Sie sind bewusst **nicht** auf reinen Lesezugriff beschränkt (falls du sie doch mal brauchst), aber in Name (Präfix "⚠️") und Icon markiert und tragen ein `warnhinweis`-Attribut (sichtbar in Entwicklertools → Zustand bzw. im Mehr-Info-Dialog der Entity). Die Dashboard-Strategy (Option A oben) fasst sie zusätzlich in einem eigenen "⚠️ Installateur-Ebene"-Bereich pro Kreis zusammen, mit dem Warnhinweis direkt als Überschrift:

- Heizkreis: Vorlauf Max, Vorlauf Min
- Warmwasser: Vorrang, Überhöhung, Nachlaufzeit, Einschalthysterese, Legionellenschutz
- Pellematic: Regeltemperatur (klassisch + Smart), Abschalttemperatur, Abgastemp-Minimum, Leistungsstufe (klassisch + Smart)

**Falsche Werte hier können die Anlage beschädigen oder Sicherheitsfunktionen beeinträchtigen** (insbesondere Kessel-Abschalttemperatur und Abgastemp-Minimum sind vermutlich Schutzparameter, keine reinen Komfort-Einstellungen). Im Zweifel am Gerät selbst mit Installateur-Code ändern, oder Rücksprache mit dem Installateur halten.

### ℹ️ Betriebsart bei Anlage "Aus"

Am Original-Gerät ist die Heizkreis-/Warmwasser-Betriebsart (`select.*_betriebsart`, sowie die Modus-Auswahl der zugehörigen `climate.*`-Entity) ausgegraut, solange die **Anlage-Betriebsart auf "Aus" steht** – eine reine UI-Ausgrauung am Gerät, kein Sicherheitsmechanismus. Diese Integration lässt das Feld deshalb weiterhin editierbar, zeigt in diesem Zustand aber ein `hinweis`-Attribut: Änderungen wirken sich erst aus, sobald die Anlage wieder auf Auto/Warmwasser gestellt wird.

### Langzeitstatistik

Sensoren mit numerischem Wert haben bereits die passende `state_class` (measurement bzw. total_increasing), wodurch Home Assistant automatisch **Langzeitstatistiken** führt (im Gegensatz zur normalen Historie verfallen diese nicht nach ein paar Tagen). Für echte Langzeit-Trends (z.B. Temperaturverlauf über Monate, oder Brennerstarts pro Tag zur Kurztakt-Analyse) nutzen sowohl die Dashboard-Strategy als auch `dashboard_example.yaml` dafür `statistics-graph`-Karten statt `history-graph`.

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

#### Dashboard-Strategy zeigt "Error loading the dashboard strategy"
Meist ein veralteter Frontend-Cache nach einem Update der Integration - Browser-Cache leeren bzw. Seite mit Strg/Cmd+Shift+R neu laden, dann Home Assistant neu starten (die Integration registriert die JS-Ressource erneut beim Start). Falls die Fehlermeldung ausdrücklich einen `ll-strategy-dashboard-...`-Elementnamen nennt, der nie registriert wurde, ist das ein Hinweis auf eine Versionsinkonsistenz zwischen `www/oekofen-strategy.js` und der geladenen Frontend-Ressource - Integration einmal komplett deaktivieren/aktivieren.

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

Automatisierte Tests laufen bei jedem Push/PR per GitHub Actions (`.github/workflows/test.yml`, Python 3.14 - dieselbe Python-Version, die die aktuell gepinnte `homeassistant`-Release voraussetzt). Lokal ausführen:

```bash
pip install -r requirements-test-ha.txt   # zieht requirements-test.txt automatisch mit
pytest tests/ -v
```

`requirements-test.txt` allein (ohne Home Assistant) reicht für `test_pellematic_api.py`, das keine HA-Abhängigkeit hat. Für die Plattform-Tests (number/select/switch/climate/time/datetime), die echte HA-Entity-Basisklassen erben, wird zusätzlich `requirements-test-ha.txt` gebraucht - es pinnt `homeassistant` exakt auf die Version, die auch live läuft, statt gegen einen zunehmend veralteten Mock zu testen.

`test_pellematic_api.py` mockt die Geräte-API nicht mit `aioresponses` (das an aiohttps internen `ClientResponse`-Konstruktor gekoppelt und bei neueren aiohttp-Versionen kaputt ist), sondern startet einen echten lokalen `aiohttp.web`-Server (`aiohttp.test_utils.TestServer`) und lässt `PellematicAPI` real dagegen sprechen - dadurch bleiben die Tests unabhängig von der jeweils installierten aiohttp-Version lauffähig.

`tests/test_readme_version.py` hält `manifest.json` (einzige Quelle der
Wahrheit für die Versionsnummer) und README.md automatisch synchron: CI
schlägt fehl, falls der Footer ("**Version**: ...") oder die passende
"### Version X.Y.Z"-Changelog-Überschrift nach einem Versions-Bump in
`manifest.json` vergessen werden.

### Getestete Konfiguration
- **ÖkOfen Pellematic 2012** - Vollständig getestet, inkl. Firmware-Varianten ("klassisch" vs. "Smart" bei Leistungsstufe/Regeltemperatur)
- **Home Assistant** - CI und Live-Betrieb laufen gegen aktuelle Releases; die Integration ist zusätzlich defensiv gegen HA-API-Änderungen aus früheren Versionen abgesichert (z.B. `OptionsFlow.config_entry`-Property-Wechsel, `StaticPathConfig` vs. älteres `register_static_path`)

### API-Endpoints (Dokumentiert und getestet)
```python
# Anmeldung
POST /index.cgi
Content-Type: application/x-www-form-urlencoded
username=...&password=...&language=de&submit=Anmelden
# Erfolg: HTTP 303 Redirect + Set-Cookie: pksession=XXXXX + LoginError=0

# Datenabfrage
POST /?action=get&attr=1
Content-Type: application/json
X-Requested-With: XMLHttpRequest
["CAPPL:LOCAL.L_aussentemperatur_ist", "CAPPL:FA[0].L_kesseltemperatur"]
```

### Bewährte Parameter
Die Integration verwendet nur getestete und funktionierende Parameter:
- `CAPPL:LOCAL.L_aussentemperatur_ist` - Außentemperatur ✅
- `CAPPL:FA[0].L_kesseltemperatur` - Kesseltemperatur ✅
- `CAPPL:FA[0].L_kesselstatus` - Kesselstatus ✅

## 📝 Changelog

### Version 0.8.1

- 🐛 **Hotfix**: Der geteilte `OekofenCoordinator` aus 0.8.0 ließ `coordinator.data`
  bis zum ersten Refresh `None` statt `{}` - da Plattformen ihre Entities schon
  vorher anlegen, crashten alle Verfügbarkeits-Checks beim Start und jede
  Entity blieb dauerhaft "nicht verfügbar". Behoben durch `self.data = {}` direkt
  nach der Coordinator-Initialisierung.
- 📊 **Feuerraumtemperatur eigenes Chart**: Lief bisher zusammen mit allen
  anderen Temperatur-Sensoren im "Temperaturverlauf"-Chart der Statistik-Ansicht -
  da Feuerraumtemperatur (Ist + Soll) 0-1000°C erreicht, während alles andere
  (Kessel/Vorlauf/Raum/Außentemp etc.) unter ~100°C bleibt, quetschte das die
  restlichen Kurven zu einer unlesbaren Linie am unteren Rand. Jetzt eigenes
  "Feuerraumtemperatur"-Chart (Ist + Soll zusammen, weiterhin vergleichbar).
- 🔄 **Cache-Busting für die Dashboard-Strategy-JS**: Wurde bisher unter einer
  fixen URL ausgeliefert, wodurch Browser nach einem Integrations-Update
  teils noch die alte, zwischengespeicherte Version geladen haben (sichtbar
  z.B. als "Timeout waiting for strategy element ... to be registered"). Die
  JS-Datei wird jetzt mit der Versionsnummer als Query-Parameter ausgeliefert,
  sodass jeder Versions-Bump automatisch einen frischen Download erzwingt.

### Version 0.8.0

- ⚡ **Coordinator-Konsolidierung**: Alle Plattformen (select/number/
  climate/sensor/switch/time/datetime/text) hatten bisher je einen
  eigenen `DataUpdateCoordinator`, der unabhängig pollte - bis zu ~11
  separate HTTP-Requests pro Zyklus gegen den eher schwachbrüstigen
  Embedded-Webserver am Kessel, teils mit überlappenden Parametern
  (z.B. `anlage_betriebsart` sowohl von select.py als auch climate.py
  einzeln abgefragt). Neuer gemeinsamer `OekofenCoordinator`
  (`coordinator.py`): jede Plattform registriert beim eigenen Setup nur
  noch ihre benötigten Parameter (`add_parameters()`), `__init__.py`
  löst danach einen einzigen ersten Refresh für den ganzen Config-Entry
  aus. Dadurch ein kombinierter Request statt bis zu elf - und da das
  jetzt günstiger ist, Poll-Intervall von 30-60s (je nach Plattform) auf
  einheitlich 15s gesenkt.
- 🧩 **Dashboard-Strategy** (`custom:oekofen-strategy`,
  `custom_components/oekofen/www/oekofen-strategy.js`): generiert das
  komplette Dashboard zur Laufzeit direkt aus den vorhandenen Entities -
  erkennt beliebig viele Heizkreis-/Warmwasser-/Zirkulationspumpen-/
  Pellematic-Kreise automatisch, inklusive aller 3 Zeitblöcke (nicht nur
  Block 1 wie in der statischen YAML-Vorlage). Wird automatisch als
  Frontend-Ressource registriert, kein `PRAEFIX`-Ersetzen nötig. Die
  Gruppierungslogik ermittelt das gemeinsame Entity-ID-Präfix des Geräts
  empirisch (längstes gemeinsames Präfix aller eigenen Entity-IDs) statt
  es zu erraten, und ordnet Entities anhand ihres deutschen Namens-Suffix
  zu (z.B. "heizkreis_1_betriebsart") - unabhängig davon, wie das Gerät
  umbenannt wurde.
  🐛 Erste Version registrierte das Custom-Element unter dem falschen
  Namen (`ll-strategy-dashboard-oekofen` statt `...-oekofen-strategy` -
  HA hängt den kompletten String nach `custom:` an, nicht nur die
  Domain) und schlug live mit *"Timeout waiting for strategy element ...
  to be registered"* fehl - behoben.
  Danach schrittweise ausgebaut: eigene **Puffer & Pumpen**-Ansicht für
  Fühler/Pumpen-Sensoren ohne Kreis-Zuordnung, eine **Statistik**-Ansicht
  (Verlaufs-/Langzeitgraphen rein anhand `device_class`/`state_class`/
  Einheit zusammengestellt, nicht anhand fester Namen), Installateur-
  Ebene-Felder bekommen einen eigenen, klar markierten Warnbereich pro
  Kreis statt zwischen den normalen Einstellungen zu stehen, und
  **Diagnose**/**Mail & SMTP** wurden aus der Übersicht in eigene
  Ansichten ausgelagert, damit die Übersicht nicht mit langen Listen
  überladen wird.
- 📱 **`dashboard_example.yaml` grundlegend überarbeitet**: von 6 auf 8
  Ansichten erweitert (neu: Zeitprogramme, Einstellungen mit Mail/SMTP/
  Fernwartung/Diagnose), Pellematic bekommt jetzt ebenfalls eine
  `thermostat`-Karte, Heizkreis/Warmwasser-Betriebsarten laufen über die
  nativen `select.*`-Entities statt der veralteten `oekofen.set_*_mode`-
  Services. Platzhalter-Schema von `DEINHOST` auf `PRAEFIX` umgestellt, da
  Entity-IDs seit v0.6.0 von Bereich+Gerätename statt Host/IP abhängen
  (siehe Abschnitt "Entity-IDs" oben - live an einer echten Anlage
  nachvollzogen, nachdem sich beim Neuanlegen der Integration der
  Gerätename geändert hatte).
- ⚙️ **Verbindungsdaten nachträglich editierbar**: Neuer Options-Flow
  (Integration → "Konfigurieren") erlaubt das Ändern von IP-Adresse,
  Benutzername, Passwort und Sprache, ohne die Integration neu einrichten
  zu müssen.
  🐛 Ursprüngliche Version brach mit `AttributeError: property
  'config_entry' has no setter` auf neueren HA-Versionen (2024.12+, dort
  ist `OptionsFlow.config_entry` eine schreibgeschützte Framework-Property)
  - behoben durch internes Speichern unter `_config_entry`.
  ⚠️ Eine zusätzliche "Gerät entfernen"-Option in diesem Dialog wurde
  testweise ergänzt und **noch am selben Abend wieder entfernt**: die
  Menüzeilen erschienen live ohne sichtbare Beschriftung (nur Pfeile),
  was zu einem versehentlichen Löschen des kompletten Konfigurationseintrags
  (380 Entities) führte. Entfernen bleibt bewusst exklusiv dem nativen,
  gut getesteten Drei-Punkte-Menü vorbehalten.
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
- ✅ **Climate-Plattform** (`climate.py`, neu): Heizkreis, Warmwasser und
  Pellematic bekommen echte `climate.*`-Entities für Thermostat-Karten in
  HA, statt nur Sensoren/Number-Feldern. Mode-Mapping ist pro Kreistyp
  konfigurierbar (`mode_map`), da die Kreise unterschiedliche Betriebsarten
  am Gerät haben:
  - **Heizkreis:** Aus → `off`, Auto → `auto`, Heizen → `heat`,
    Absenken → `heat` + Preset "Absenken" (kein HA-Standardmodus, daher als
    Preset statt als eigener hvac_mode).
  - **Warmwasser:** Aus → `off`, Auto → `auto`, Ein → `heat`, plus Preset
    "Boost" für "Einmal Aufbereiten" (zusätzlich zum eigenständigen `switch.*`).
  - **Pellematic:** Aus → `off`, Auto → `auto`, Ein → `heat` (gleiches
    3-Zustands-Modell wie Warmwasser, kein Preset).
  - Ist-/Solltemperatur und Min/Max-Grenzen kommen aus denselben
    CAPPL-Parametern wie die bestehenden Sensor-/Number-Entities für den
    jeweiligen Kreis - keine Doppelquelle für dieselben Werte.
- 🐛 Korrektur: Preset heißt jetzt wörtlich **"Absenken"** statt des
  irreführenden generischen HA-Begriffs "Eco".
- 🧪 **Testinfrastruktur**: `test_pellematic_api.py` mockt die Geräte-API
  jetzt über einen echten lokalen `aiohttp.web`-Server statt über
  `aioresponses` (das an aiohttps internen `ClientResponse`-Konstruktor
  gekoppelt und seit aiohttp 3.10+ kaputt ist - `TypeError:
  ClientResponse.__init__() missing 'stream_writer'`, live reproduziert).
  Damit entfällt der künstliche `aiohttp<3.10`-Deckel, der sich zuvor mit
  Home Assistants eigenem exaktem aiohttp-Pin gebissen und das Testen
  gegen aktuelle, nicht-verwundbare HA-Releases blockiert hat. CI
  (`.github/workflows/test.yml`) läuft jetzt auf Python 3.14 gegen ein
  fest gepinntes, aktuelles `homeassistant`-Release (dieselbe Version, die
  auch live eingesetzt wird), statt gegen ein unversioniert "neuestes"
  `homeassistant`, das zuvor mangels passender Python-Version auf einem
  veralteten, teils verwundbaren Release landete.
- 🐛 Glühstab-Zündzeit (`sensor.*_gluhstab_zundzeit`) verlor ihren Wert bei
  jedem HA-Neustart (fiel auf "unknown" zurück, obwohl der letzte reale
  Zündvorgang oft Stunden/Tage zurücklag) - Entity nutzt jetzt
  `RestoreSensor` und stellt den letzten bekannten Wert beim Start wieder her.

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
  benötigen keine `input_number`/`input_select`-Helfer mehr.

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

**Version**: 0.8.1
**Status**: Aktiv weiterentwickelt - basierend auf umfangreichen Tests gegen ein echtes Gerät
