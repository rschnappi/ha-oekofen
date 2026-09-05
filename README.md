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

## 📱 Dashboard

Zwei Wege zu einem fertigen Dashboard - für die meisten reicht **Option A**.

### Option A: Automatisch generiertes Dashboard (empfohlen)

Die Integration legt beim Start automatisch ein eigenes Dashboard **"ÖkOfen"** an (sichtbar in der Seitenleiste, Pfad `/oekofen`) und baut dessen Inhalt **serverseitig aus den tatsächlich vorhandenen Entities** zusammen - kein Suchen-und-Ersetzen von Platzhaltern, keine manuelle Pflege bei mehreren Heizkreisen, keine Einrichtung nötig.

Bis Version 0.9.8 geschah das über eine clientseitige [Lovelace-Dashboard-Strategy](https://www.home-assistant.io/dashboards/strategies/) (JavaScript, im Browser ausgeführt). Seit 0.10.0 generiert die Integration stattdessen ein ganz normales, statisches Dashboard direkt in Python und speichert es über HAs eigene Dashboard-Storage-API - denselben Mechanismus, mit dem HA selbst das Onboarding-Dashboard "Karte" anlegt. Grund: eine Dashboard-Strategy bekommt von HAs Frontend nur wenige Sekunden Zeit, sich zu registrieren, sonst "Timeout waiting for strategy element ... to be registered" - ein Wettlauf, den ein kalt gestarteter Client (Kiosk-Tablet direkt nach einem Neustart, langsames WLAN) verlässlich verlieren kann, ganz unabhängig von Caching. Ein normales, serverseitig generiertes Dashboard hat dieses Problem grundsätzlich nicht: HA rendert es wie jedes von Hand angelegte Dashboard, garantiert bei jedem Laden.

Das Dashboard wird automatisch aktuell gehalten:
- **Bei jedem Neustart/Reload** der Integration (nachdem der erste Koordinator-Refresh durchgelaufen ist, damit Installateur-Warnhinweise & Co. schon echte Werte haben).
- **Automatisch**, sobald sich der erkannte Wartungstermin-Kalender ändert (neuer/geänderter/gelöschter Termin) - kein Neustart nötig.
- **Manuell** über den Dienst **ÖkOfen: Dashboard neu erzeugen** (`oekofen.regenerate_dashboard`), z. B. nach Änderungen an Entities.

**Was generiert wird** (pro Gerät, automatisch angepasst an die vorhandene Hardware):
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

Ein Teil der Sollwerte ist am Original-Gerät selbst **hinter dem Installateur-/Techniker-Code** (`main.codeebene`) versteckt – am Touchdisplay bzw. in der Geräte-Weboberfläche kommt man ohne diesen Code gar nicht an sie heran. Diese Integration liest das Gerät über dieselbe API an, die auch die Weboberfläche nutzt, und kann diese Werte deshalb technisch trotzdem schreiben. Sie sind bewusst **nicht** auf reinen Lesezugriff beschränkt (falls du sie doch mal brauchst), aber in Name (Präfix "⚠️") und Icon markiert und tragen ein `warnhinweis`-Attribut (sichtbar in Entwicklertools → Zustand bzw. im Mehr-Info-Dialog der Entity). Das automatisch generierte Dashboard (Option A oben) fasst sie zusätzlich in einem eigenen "⚠️ Installateur-Ebene"-Bereich pro Kreis zusammen, mit dem Warnhinweis direkt als Überschrift:

- Heizkreis: Vorlauf Max, Vorlauf Min
- Warmwasser: Vorrang, Überhöhung, Nachlaufzeit, Einschalthysterese, Legionellenschutz
- Pellematic: Regeltemperatur (klassisch + Smart), Abschalttemperatur, Abgastemp-Minimum, Leistungsstufe (klassisch + Smart)

**Falsche Werte hier können die Anlage beschädigen oder Sicherheitsfunktionen beeinträchtigen** (insbesondere Kessel-Abschalttemperatur und Abgastemp-Minimum sind vermutlich Schutzparameter, keine reinen Komfort-Einstellungen). Im Zweifel am Gerät selbst mit Installateur-Code ändern, oder Rücksprache mit dem Installateur halten.

### ℹ️ Betriebsart bei Anlage "Aus"

Am Original-Gerät ist die Heizkreis-/Warmwasser-Betriebsart (`select.*_betriebsart`, sowie die Modus-Auswahl der zugehörigen `climate.*`-Entity) ausgegraut, solange die **Anlage-Betriebsart auf "Aus" steht** – eine reine UI-Ausgrauung am Gerät, kein Sicherheitsmechanismus. Diese Integration lässt das Feld deshalb weiterhin editierbar, zeigt in diesem Zustand aber ein `hinweis`-Attribut: Änderungen wirken sich erst aus, sobald die Anlage wieder auf Auto/Warmwasser gestellt wird.

### Langzeitstatistik

Sensoren mit numerischem Wert haben bereits die passende `state_class` (measurement bzw. total_increasing), wodurch Home Assistant automatisch **Langzeitstatistiken** führt (im Gegensatz zur normalen Historie verfallen diese nicht nach ein paar Tagen). Für echte Langzeit-Trends (z.B. Temperaturverlauf über Monate, oder Brennerstarts pro Tag zur Kurztakt-Analyse) nutzen sowohl das automatisch generierte Dashboard als auch `dashboard_example.yaml` dafür `statistics-graph`-Karten statt `history-graph`.

⚠️ **Wichtig bei einem Update von Version < 0.4.0**: Diese Version hat das `unique_id`-Schema der Sensoren geändert (siehe Changelog), wodurch sich auch die Entity-IDs ändern. Das **unterbricht die Kontinuität bereits gesammelter Langzeitstatistiken** – die alten Sensoren behalten ihre Historie, werden aber nicht mehr aktualisiert; die neuen Sensoren starten bei null. Um die Historie zu erhalten, kannst du nach dem Update die alte, verwaiste Entity löschen und die neue Entity in **Einstellungen → Entitäten → [Entity] → Einstellungen → Entity-ID** auf die alte ID umbenennen – Home Assistant führt die Statistik dann unter derselben Statistik-ID (die am Entity-ID-String hängt) nahtlos weiter.

## 🗓️ Wartungstermin automatisch vorbereiten (Blueprint)

`blueprints/automation/oekofen/` enthält ein 3-teiliges Blueprint-Set: Anlage
am Abend vor einem Kalendertermin ("Rauchfangkehrer", "Service Ofen", ...)
automatisch ausschalten (Zustand vorher in einer Szene sichern), und nach
dem Termin per Knopfdruck in der Benachrichtigung wieder zurückstellen.
Braucht keine Code-Änderung an der Integration - nur Bordmittel von Home
Assistant (Kalender, Szenen, Benachrichtigungs-Aktionen). Siehe das
[README im Blueprint-Ordner](blueprints/automation/oekofen/README.md) für
Installation und Konfiguration.

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

#### Dashboard "ÖkOfen" fehlt oder zeigt veraltete Inhalte
Seit 0.10.0 kein clientseitiges Problem mehr (siehe oben) - das Dashboard wird serverseitig generiert und gespeichert. Fehlt es trotzdem: prüfen, ob die Integration erfolgreich eingerichtet ist (**Einstellungen → Geräte & Dienste**) und ob `lovelace` überhaupt aktiv ist (Standard bei jeder normalen HA-Installation). Zeigt es veraltete Inhalte nach einer Änderung: Dienst **ÖkOfen: Dashboard neu erzeugen** (`oekofen.regenerate_dashboard`) aufrufen.

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

### Version 0.10.1

- 🐛 **Fix: Dashboard erschien nach 0.10.0 gar nicht mehr** - `hass.data["lovelace"]`
  ist seit einem HA-Core-Refactor (spätestens ab 2024, live gegen 2026.9.0
  bestätigt) ein `LovelaceData`-Dataclass-Objekt statt eines Dicts, wodurch
  der dict-artige Zugriff aus 0.10.0 mit `AttributeError: 'LovelaceData'
  object has no attribute 'get'` fehlschlug - die Integration blieb dadurch
  im Setup hängen, kein Dashboard wurde je angelegt. Zusätzlich hält HA-Core
  die für das Anlegen neuer Dashboards nötige `DashboardsCollection`
  inzwischen nur noch als lokale Variable innerhalb der lovelace-Integration
  selbst, nirgends über `hass.data` erreichbar - andere Integrationen können
  seither nicht mehr direkt darauf zugreifen. Die Integration legt jetzt eine
  eigene `DashboardsCollection`-Instanz an (dieselbe zugrunde liegende
  Storage-Datei, daher dauerhaft kompatibel mit dem, was HA beim nächsten
  Neustart selbst einliest), registriert das Sidebar-Panel und den
  In-Memory-Eintrag für den laufenden Boot manuell, und ergänzt den
  Erstellungs-Payload um `allow_single_word` (der URL-Pfad "oekofen" enthält
  keinen Bindestrich, den HA-Core sonst verlangt). Gegen den exakten
  `homeassistant==2026.9.0`-Quellcode verifiziert (Schema-Validierung,
  Klassenschnittstellen).

### Version 0.10.0

- 🏗️ **Dashboard wird jetzt serverseitig generiert, nicht mehr als
  clientseitige Dashboard-Strategy**: Trotz mehrerer Anläufe (siehe 0.9.2,
  0.9.4, 0.9.8) blieb "Timeout waiting for strategy element ... to be
  registered" ein Problem - der eigentliche Grund war struktureller Natur,
  nicht Caching: HA's Frontend gibt einem Custom-Strategy-Element nur
  wenige Sekunden Zeit, sich selbst zu registrieren, und ein kalt
  gestarteter Client (Kiosk-Tablet direkt nach einem Neustart) kann dieses
  Rennen verlieren, egal wie zuverlässig das JS selbst ausgeliefert wird.
  Die komplette View-Logik ist jetzt nach Python portiert
  (`custom_components/oekofen/dashboard.py`) und erzeugt ein ganz normales,
  statisches Dashboard über HAs eigene Lovelace-Speicher-API - denselben
  Mechanismus, mit dem HA selbst das Onboarding-Dashboard "Karte" anlegt.
  Kein Custom Element mehr, kein Registrierungs-Timeout mehr möglich, keine
  JS-Datei mehr im Repo. Das Dashboard ("ÖkOfen", in der Seitenleiste) wird
  automatisch beim Setup/Neustart und bei jeder Änderung des
  Wartungstermin-Kalenders aktualisiert, zusätzlich manuell über den neuen
  Dienst `oekofen.regenerate_dashboard`.

### Version 0.9.8

- 🐛 **Fix "Timeout waiting for strategy element ... to be registered"**:
  Die Dashboard-Strategy-JS wurde seit 0.9.2 mit `no-store` ausgeliefert,
  musste also bei *jedem* Dashboard-Aufruf frisch über's Netz geladen
  werden - und zwar innerhalb der wenigen Sekunden, die HA's Frontend einem
  Custom-Strategy-Element zum Registrieren einräumt. Im Desktop-Browser
  (LAN, Millisekunden) fiel das kaum auf, ein langsamer/kalt gestarteter
  Client (z. B. die Companion-App-WebView) hat die Frist dagegen
  reproduzierbar gerissen. Die Datei wird jetzt wieder normal cachebar
  ausgeliefert (`immutable`, plus ETag/304 für Clients, die trotzdem
  revalidieren) - unbedenklich, weil die URL durch einen Hash des
  Datei-Inhalts cachegebustet ist (`?v=<hash>`), nicht mehr durch die
  manuell zu pflegende `manifest.json`-Version. Jeder Client lädt eine
  Version genau einmal und registriert die Strategy danach lokal aus dem
  Cache. Da der Hash automatisch aus dem tatsächlichen Dateiinhalt berechnet
  wird, kann ein vergessener Versions-Bump diesen Mechanismus nicht mehr
  außer Kraft setzen.

### Version 0.9.6

- 📊 **Neue Sensoren "Softstartdauer" und "Nachlaufdauer"**: Dauer der
  letzten "Softstart"- bzw. "Nachlauf"-Phase des Kesselstatus, in Minuten -
  gleicher `_KesselstatusPhaseDuration`-Mechanismus wie bei Zündzeit und
  Saugdauer, jeweils mit eigenem 7-Tage-Verlaufs- plus
  90-Tage-Langzeitstatistik-Chart im Dashboard. Übersteht HA-Neustarts
  (auch mitten in einer laufenden Phase). Keine Warnschwelle/Benachrichtigung.
- 🧹 Dashboard-Strategy: die vier Phasen-Dauer-Charts (Zündzeit, Saugdauer,
  Softstartdauer, Nachlaufdauer) teilen sich jetzt einen gemeinsamen
  `phaseDurationCards()`-Helper statt vier fast identischer Code-Blöcke.

### Version 0.9.5

- 📊 **Neuer Sensor "Saugdauer"**: Dauer der letzten "Saugen"-Phase
  (Pellet-Förderung per Unterdruck) des Kesselstatus, in Minuten - analog
  zur bestehenden Glühstab-Zündzeit (gleicher zugrunde liegende
  Mechanismus, `_KesselstatusPhaseDuration` in `ignition_diagnostics.py`,
  jetzt für beide gemeinsam genutzt). Übersteht HA-Neustarts (auch
  mitten in einer laufenden Saugphase) und bekommt ein eigenes
  7-Tage-Verlaufs- plus 90-Tage-Langzeitstatistik-Chart im Dashboard,
  genau wie die Zündzeit. Keine Warnschwelle/Benachrichtigung (die ist
  spezifisch für Glühstab-Verschleiß).

### Version 0.9.4

- 🐛 **Zündzeit zeigte trotz 0.9.3 weiter Sekunden statt Minuten an.**
  Ursache live gefunden: Home Assistant's eigener `SensorEntity`-Code
  "pinnt" die Anzeige-Einheit einer Duration-Sensor-Entity automatisch
  auf die zuerst gesehene Einheit, sobald sich die native Einheit einer
  bereits bestehenden Entity ändert - explizit dafür gedacht, bestehende
  Statistiken/Dashboards nicht durch einen Integrations-Update kaputt
  zu machen. Genau das ist beim Wechsel von Sekunden auf Minuten
  passiert: neue Werte in Minuten wurden weiterhin zurück in Sekunden
  umgerechnet angezeigt (z.B. "492 s" statt "8,2 min"). Dieses Pinning
  wird jetzt beim Start einmalig aufgehoben.
- 🔄 **Reload-Button im Dashboard**: Neben der Versionsnummer oben in der
  Übersicht gibt es jetzt einen Button, der die Seite neu lädt - eine
  manuelle Möglichkeit, eine evtl. noch veraltete Dashboard-Ansicht
  aufzufrischen, ohne im Browser den Cache manuell leeren zu müssen.

### Version 0.9.3

- 🔄 **Glühstab Zündzeit/Warnschwelle jetzt in Minuten statt Sekunden.**
  `sensor.*_gluhstab_zundzeit` und `number.*_gluhstab_warnschwelle` (Bereich
  jetzt 1-15 min statt 30-900s, Default weiterhin 10 min = vorher 600s)
  zeigen ihre Werte in Minuten. Ein zuvor gespeicherter Sekunden-Wert wird
  beim ersten Neustart nach dem Update automatisch umgerechnet
  (Erkennung: Werte über 60 können bei den neuen Grenzen nur ein
  Sekunden-Restwert sein), nicht einfach als "600 min" fehlinterpretiert.
- 📊 **Eigenes Zündzeit-Chart in der Statistik-Ansicht**: Lief bisher als
  einfache Kachel im "Betriebsstunden & Zyklen"-Grid ohne Verlauf. Hat
  jetzt ein eigenes 7-Tage-Verlaufs-Chart (die Warnschwelle als
  Referenzlinie mit eingeblendet) plus 90-Tage-Langzeitstatistik
  (Mittelwert/Min/Max pro Tag), analog zum Feuerraumtemperatur-Chart.

### Version 0.9.2

- 🐛 **Dashboard-Strategy-JS wird jetzt mit explizitem `Cache-Control:
  no-store` ausgeliefert.** Trotz Versions-basiertem Cache-Bust
  (0.8.1) und dem Frontend-Registrierungs-Reihenfolge-Fix (0.8.4) blieb
  der Fehler "Timeout waiting for strategy element ... to be
  registered" auf manchen Clients (v.a. Kiosk-Tablets) unzuverlässig
  bestehen: funktionierte nach Cache-Leeren für 1-2 Aufrufe, dann wieder
  nicht. HA's eingebauter Static-Path-Helfer (`cache_headers=False`)
  setzt dabei keinen expliziten Cache-Control-Header - überlässt es
  also den Heuristiken des jeweiligen Browsers/WebViews, ob und wie
  lange die Datei trotzdem lokal zwischengespeichert wird. Die JS-Datei
  wird jetzt über eine eigene View mit explizitem `no-store`-Header
  ausgeliefert statt über den Static-Path-Helfer, was diese Unschärfe
  beseitigt.

### Version 0.9.1

- ✅ **Reauth-Flow**: Ändert sich das Techniker-Passwort am Gerät, schlug
  die Anmeldung bisher stumm dauerhaft fehl - Entities wurden "nicht
  verfügbar", ohne dass HA irgendeinen Hinweis darauf gab, warum oder wie
  das zu beheben ist. Sowohl beim initialen Setup als auch bei jedem
  regulären Poll-Fehlschlag wird ein reiner Authentifizierungsfehler jetzt
  erkannt und löst eine "Anmeldung erneuern"-Aufforderung in
  **Einstellungen → Geräte & Dienste** aus, über die neue Zugangsdaten
  eingegeben werden können, ohne die Integration neu einzurichten.

### Version 0.9.0

- 🐛 **`sensor.py` erzeugte nie mehr als 1 Sensor-Satz pro Pellematic-/
  Heizkreis-/Warmwasser-Einheit**, unabhängig davon, wie viele die
  Discovery tatsächlich gefunden hat - im Gegensatz zu allen anderen
  Plattformen (`climate.py`, `number.py`, `select.py`, `switch.py`,
  `time.py`, `datetime.py`), die schon länger dynamisch pro entdecktem
  Kreis bauen. Ein zweiter Heizkreis/Warmwasser-Kreis/Pellematic-Kessel
  bekam dadurch stillschweigend keinerlei Sensoren (Kesselstatus,
  Vorlauftemperatur, Lüfterdrehzahl, Pelletsfüllstand, Motorstatus, …).
  `sensor.py` baut die Pellematic-/Heizkreis-/Warmwasser-Abschnitte jetzt
  ebenfalls dynamisch pro entdecktem Kreis. Bei nur je einem Kreis pro Typ
  (der bisher einzige getestete Fall) ändert sich nichts - exakt dieselben
  Entity-IDs/Namen wie bisher.

### Version 0.8.9

- 🐛 **Glühstab-Zündzeit verlor eine laufende Zündung bei einem Neustart
  mitten im Zündvorgang.** Nur der fertige Wert wurde bisher über HA-
  Neustarts hinweg gespeichert (RestoreSensor), nicht der interne
  "seit wann läuft die aktuelle Zündung"-Zeitstempel - ein Neustart genau
  während einer Zündung verlor diesen Zeitpunkt, wodurch die Dauer dieses
  Zyklus beim Abschluss nie berechnet oder gegen die Warnschwelle
  geprüft wurde (kein Crash, nur eine stillschweigend übersprungene
  Messung). Wird jetzt zusätzlich mitgespeichert und wiederhergestellt.

### Version 0.8.8

- 🐛 **`set_data()` rundete Divisor-Werte nicht, sondern kappte sie**
  (`int()` statt `round()`): Bei Fließkomma-Werten, die knapp unter eine
  Ganzzahl fallen (z.B. `2.3 * 100 == 229.99999999999997`), wurde am
  Gerät ein Rohwert geschrieben, der 1 Einheit zu niedrig war. Divisor=10
  (bislang einziger Fall in den Tests) trifft das Problem zufällig nicht.

### Version 0.8.7

- 🐛 **"Puffer & Pumpen"-Dashboard-Ansicht war toter Code**: Der Matching-
  Regex in der Strategy-JS erwartete deutsche Namensfragmente
  (`puffer…`/`pumpe…`/`tpm…`/`tpo…`), während `sensor.py`'s
  Puffer-/Pumpen-Sensoren tatsächlich englisch benannt sind
  (`buffer_top_temperature`, `buffer_pump`, `supply_pump`,
  `circulation_pump_speed`). Der Regex matchte dadurch **nie** - diese
  Sensoren landeten auf jeder Installation im generischen
  Diagnose-Karton statt in einer eigenen Ansicht. Regex/Labels an die
  tatsächlichen Sensor-Keys angepasst.
- 🔋 Zwei rein lokale, nie pollende Entities (`Integration Version`,
  `Glühstab Warnschwelle`) markieren sich jetzt korrekt als
  `should_poll = False`.

### Version 0.8.6

- ℹ️ **Versionsnummer im Dashboard**: Neuer diagnostischer Sensor
  "Integration Version" (liest `manifest.json` beim Start, kein
  Geräte-Parameter) - die Dashboard-Strategy zeigt ihn jetzt als kleine
  Notiz ganz oben in der Übersicht ("ÖkOfen Integration vX.Y.Z"), damit
  auf einen Blick klar ist, welche Version tatsächlich läuft.

### Version 0.8.5

- 🎛️ **hvac_mode-Buttons direkt auf der Thermostat-Karte**: 0.8.3 hatte nur
  die Preset-Auswahl (Absenken/Boost) direkt sichtbar gemacht - die
  Modus-Auswahl (Aus/Auto/Heizen) war weiterhin nur über den Mehr-Info-
  Dialog erreichbar, bei Pellematic (ohne Presets) fehlte dadurch jede
  direkte Bedienmöglichkeit auf der Karte. Zusätzliches
  `climate-hvac-modes`-Feature ergänzt, für alle drei Kreistypen.

### Version 0.8.4

- 🐛 **Fix: "Timeout waiting for strategy element ... to be registered"
  direkt nach einem HA-Neustart.** War keine Cache-Sache, wie zuerst
  angenommen: `_async_register_frontend_resources()` (registriert die
  Dashboard-Strategy-JS) lief bisher *nach* der Geräte-Authentifizierung
  und Kreis-Discovery - beides echte Netzwerk-Roundtrips zum Kessel, die
  ein paar Sekunden dauern können. Lädt ein Client (z.B. ein Tablet, das
  sofort nach Erreichbarkeit von HA/Frontend neu verbindet) das Dashboard
  in diesem Fenster, bekommt er die Seite noch ohne das Script-Tag
  ausgeliefert. Die Registrierung läuft jetzt als Erstes in
  `async_setup_entry`, vor jeglichem Netzwerkzugriff.

### Version 0.8.3

- 🎛️ **Preset-Buttons direkt auf der Thermostat-Karte**: Bei Heizkreis/
  Warmwasser war die Preset-Auswahl (Absenken bzw. Boost) bisher nur über
  den Mehr-Info-Dialog der Entity erreichbar. Die Dashboard-Strategy
  fügt der `thermostat`-Karte jetzt ein `climate-preset-modes`-Feature
  hinzu, das die Preset-Buttons direkt anzeigt. Pellematic bleibt
  unverändert (hat keine Presets).

### Version 0.8.2

- 💥 **Breaking: die 5 `oekofen.*`-Services entfernt** (`set_parameter`,
  `set_system_mode`, `set_heating_mode`, `set_hot_water_mode`,
  `set_pellematic_mode`). Die vier Modus-Services waren seit Einführung der
  `climate.*`/`select.*`-Entities ohnehin nur noch redundante Legacy-Pfade
  zu denselben Parametern - mit dem Nachteil, dass sie bei **mehreren**
  ÖkOfen-Geräten in derselben HA-Instanz beim zweiten Geräte-Setup
  unbemerkt die Services des ersten überschrieben hätten (Services sind
  domain-, nicht entry-weit registriert), Befehle also am falschen Kessel
  ankommen konnten. Bestehende Automationen, die einen dieser Services
  aufrufen, bitte auf die entsprechenden Entity-Services umstellen:
  `climate.set_hvac_mode`/`climate.set_preset_mode` (Betriebsart) bzw.
  `select.select_option` bzw. direktes Setzen der `number.*`-Entity für
  Parameter ohne eigene Entity.

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

**Version**: 0.10.1
**Status**: Aktiv weiterentwickelt - basierend auf umfangreichen Tests gegen ein echtes Gerät
