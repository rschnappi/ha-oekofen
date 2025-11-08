# ÖkOfen Pellematic Home Assistant Integration

Eine custom Home Assistant Integration für ÖkOfen Pellematic Heizsysteme, die auf umfangreichen Tests und Analysen basiert.

## 🔥 Version 0.3.0 - Mit Sprachunterstützung und Services

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

### Wichtige Erkenntnisse
- ✅ Neuere Firmware verwendet `username`/`password` (nicht `user`/`pass`)
- ✅ Login verwendet Form-Daten, Datenabfrage verwendet JSON
- ✅ Ohne Authentication leitet das Gerät auf `/login.cgi` um
- ✅ Session-Cookie hat 600 Sekunden Timeout

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

## 🎛️ Services

Die Integration bietet folgende Services zum Steuern des Heizsystems:

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

### Installation des Dashboards
1. Gehen Sie zu **Einstellungen** → **Dashboards**
2. Klicken Sie auf **+ Dashboard hinzufügen**
3. Wählen Sie **Neue Ansicht aus YAML erstellen**
4. Kopieren Sie den Inhalt aus `dashboard_example.yaml`
5. Das Dashboard zeigt:
   - **Übersicht**: Betriebsarten und wichtigste Sensoren
   - **Pellematic**: Kessel, Pellets, Störungen
   - **Heizkreis**: Temperaturen und Einstellungen
   - **Warmwasser**: Status und Einstellungen
   - **Puffer & Pumpen**: Pufferspeicher und Pumpen
   - **Statistiken**: Betriebsstunden, Verbrauch, Verlaufsgraphen

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

**Version**: 0.0.1  
**Letzte Aktualisierung**: November 2025  
**Status**: Stabil - Basierend auf umfangreichen Tests