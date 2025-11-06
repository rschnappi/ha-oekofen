# ÖkoFen Pellematic Smart XS Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/rschnappi/ha-oekofen.svg)](https://github.com/rschnappi/ha-oekofen/releases)
[![License](https://img.shields.io/github/license/rschnappi/ha-oekofen.svg)](LICENSE)

Eine umfassende Home Assistant Custom Component für ÖkoFen Pellematic Smart XS Pelletkessel mit robustem Session-Management und erweiterten Systemparametern.

## 🔥 Features

- **🔐 Robustes Session-Management** mit automatischer Timeout-Erkennung und Re-Authentication
- **Vollständige API-Integration** mit ÖkoFen Pellematic Steuerung
- **80+ Sensoren** für komplette Systemüberwachung
- **Erweiterte Heizkurven-Parameter** (Steigung, Fußpunkt, Heizgrenzen)
- **Warmwasser-Kreislauf Überwachung** mit allen Temperaturen und Modi
- **Aschesystem-Monitoring** inkl. Schneckendrehzahl und externe Aschebox
- **Turbinen- und Reinigungssystem** Parameter
- **Debug-Modus** mit allen verfügbaren Parametern
- **Konfigurierbare Gerätenamen** über UI
- **Automatische Wert-Parsing** (formatTexts, Timestamps, Divisoren)
- **🆕 STEUERUNG & AUTOMATION** - Änderungen an ÖkOfen senden
- **🆕 HOME ASSISTANT SERVICES** - 5 Services für komplette Kontrolle
- **🆕 SWITCH ENTITÄTEN** - Warmwasser Auto-Modus, Einmal-Aufbereitung

## 🔒 Session-Management (v1.8.2)

Die Integration verfügt über ein robustes Session-Management System:

### ✅ **Automatische Session-Verwaltung:**
- **Session-Timeout-Erkennung**: Automatische Erkennung abgelaufener Sessions
- **Auto-Re-Authentication**: Transparente Neu-Anmeldung bei Session-Verlust
- **Retry-Mechanismus**: Intelligente Wiederholung bei temporären Fehlern
- **Error-Handling**: Robuste Behandlung von 403/401 HTTP-Codes und Redirects

### 🔧 **Technische Details:**
```python
# Session-Validierung
async def _check_session_valid() -> bool
# Automatische Re-Authentication  
async def _ensure_authenticated() -> bool
# Verbesserte Retry-Logic in fetch_data() und set_parameter()
```

**Vorteile**: Keine manuellen Neustarts bei Session-Problemen, stabilere Datenerfassung, bessere Zuverlässigkeit

## 📊 Verfügbare Sensoren

### Basis System (11 Kern-Sensoren)
- Außentemperatur
- Puffertemperatur  
- Feuerraumtemperatur
- Kesseltemperatur
- Abgastemperatur
- Behälter leer/Reserve Status
- Gesamtlaufzeit & Kessellaufzeit
- Anzahl Zyklen
- Pellematic Status

### 🔧 Heizkreis-Parameter (pro Heizkreis)
- **Basis-Temperaturen**: Ist/Soll Raumtemperatur, Vorlauftemperatur
- **Heizkurven-Einstellungen**: 
  - Heizkurve Steigung
  - Heizkurve Fußpunkt  
  - Heizgrenze Heizen/Absenken
- **Erweiterte Regelung**:
  - Vorhaltezeit
  - Raumfühler Einfluss
  - Raumtemp Plus Anpassung
- **Betriebsmodus & Programm**: Aktives Programm, Pumpe Status

### 🌊 Warmwasser-System (pro Warmwasser-Kreislauf)
- Betriebsart (Heizen/Absenken/Aus)
- Temperatur Heizen/Absenken
- Einmal-Aufbereitung Status
- Aktives Zeitprogramm
- Ein-/Ausschaltfühler Temperaturen
- Warmwasser-Pumpe Status

### ⚙️ Erweiterte System-Parameter  
- **Kessel-Details**: Kesselstatus, Soll-Temperatur Anzeige
- **Aschesystem**: Ascheschnecke Drehzahl, Externe Aschebox
- **Turbine & Reinigung**: Vacuum-Takt/Pause, Saugintervall, Reinigungszeiten
- **Lüfter-System**: Lüfter-/Saugzug-Drehzahl, Unterdruck
- **Betriebszeiten**: Einschub-Laufzeit, Pausenzeit, Saugintervall
- **System-Status**: Fehler-Counter, Fernwartung, Verfügbarkeitsprüfungen

### 🐛 Debug-Modus
Im Debug-Modus werden **alle 80+ verfügbaren Parameter** als Sensoren angelegt, einschließlich:
- Alle internen Systemwerte
- Rohwerte aller Sensoren  
- Detaillierte Steuerungsparameter
- Zusätzliche Diagnose-Informationen

## 🎛️ Steuerung & Automation

### 🔧 Home Assistant Services
Die Integration bietet 5 Services für vollständige ÖkOfen-Kontrolle:

#### `ofen.set_parameter`
Direkte Parameter-Kontrolle
```yaml
service: ofen.set_parameter
data:
  parameter: "CAPPL:LOCAL.ww[0].betriebsart[1]"
  value: "0"  # 0=Aus, 1=Heizen, 2=Auto
```

#### `ofen.set_hot_water_mode`
Warmwasser-Modus setzen
```yaml
service: ofen.set_hot_water_mode
data:
  hw_index: 0     # Warmwasser-Kreislauf (meist 0)
  mode: "auto"    # off/heat/auto
```

#### `ofen.set_room_temperature` 
Raumtemperatur-Sollwert
```yaml
service: ofen.set_room_temperature
data:
  hc_index: 0        # Heizkreis-Index
  temperature: 21.5  # Zieltemperatur in °C
```

#### `ofen.set_hot_water_temperature`
Warmwasser-Temperatur
```yaml
service: ofen.set_hot_water_temperature
data:
  hw_index: 0
  temp_type: "heizen"    # heizen/absenken
  temperature: 55.0      # Temperatur in °C
```

#### `ofen.set_heating_circuit_mode`
Heizkreis-Modus
```yaml
service: ofen.set_heating_circuit_mode
data:
  hc_index: 0
  mode: "1"    # Modus-Wert
```

### 🔘 Switch Entitäten
- **Warmwasser Auto-Modus**: Ein/Aus für automatische Warmwasser-Regelung
- **Einmal-Aufbereitung**: Trigger für einmalige Warmwasser-Bereitung
- **Zusätzliche Attribute**: Aktuelle Modi, Temperaturen, Status

### 🤖 Automatisierungs-Beispiele

**Warmwasser nachts abschalten:**
```yaml
automation:
  - alias: "ÖkOfen: Warmwasser Nachtabsenkung"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: ofen.set_hot_water_mode
      data:
        hw_index: 0
        mode: "0"  # Aus
```

**Temperatur bei Anwesenheit erhöhen:**
```yaml
automation:
  - alias: "ÖkOfen: Temperatur bei Heimkehr"
    trigger:
      platform: state
      entity_id: person.max_mustermann
      to: "home"
    action:
      service: ofen.set_room_temperature
      data:
        hc_index: 0
        temperature: 22.0
```

## 🚀 Installation

### HACS Installation (Empfohlen)
1. Öffne HACS in Home Assistant
2. Gehe zu "Integrationen" 
3. Klicke "Explore & Download Repositories"
4. Suche nach "ÖkoFen Pellematic"
5. Klicke "Download"
6. Starte Home Assistant neu

### Manuelle Installation
1. Kopiere den `custom_components/ofen` Ordner in dein Home Assistant `custom_components` Verzeichnis
2. Starte Home Assistant neu
3. Gehe zu "Einstellungen" > "Geräte & Services" > "Integration hinzufügen"
4. Suche nach "ÖkoFen Pellematic"

## ⚙️ Konfiguration

1. **Integration hinzufügen**:
   - Gehe zu Einstellungen > Geräte & Services
   - Klicke "Integration hinzufügen"
   - Suche "ÖkoFen Pellematic"

2. **Verbindungsdaten eingeben**:
   - **Host**: IP-Adresse deiner Pellematic Steuerung (z.B. `192.168.1.100`)
   - **Passwort**: Dein Pellematic Passwort
   - **Gerätename**: Anzeigename (z.B. "ÖkoFen Kessel")
   - **Debug Modus**: Aktiviert alle 80+ Parameter (optional)

3. **Verbindung testen**: Die Integration testet automatisch die Verbindung

## 🔧 Erweiterte Konfiguration

### Debug-Modus
```yaml
# Aktiviert alle verfügbaren Parameter als Sensoren
debug_mode: true
```

### Anpassbare Gerätenamen
- Standardname: "ÖkoFen Pellematic"
- Anpassbar über Konfiguration UI
- Alle Sensor-Namen werden entsprechend aktualisiert

## 📈 Sensor-Übersicht

| Kategorie | Normal Modus | Debug Modus | Beschreibung |
|-----------|--------------|-------------|--------------|
| **Basis-System** | 11 | 11 | Kern-Temperaturen und Status |
| **Heizkreise** | ~20 pro HK | ~20 pro HK | Vollständige HK-Parameter |
| **Warmwasser** | ~5 pro WW | ~5 pro WW | WW-Temperaturen und Modi |
| **Erweitert** | ~25 | ~25 | Asche, Turbine, Lüfter |
| **Debug-Parameter** | 0 | ~40+ | Alle Rohwerte und interne Parameter |
| **Gesamt** | **~40-60** | **~80+** | Je nach Konfiguration |

## 🛠️ Fehlerbehebung

### Verbindungsprobleme
```
Fehler: "Verbindung fehlgeschlagen"
```
**Lösung**:
- IP-Adresse überprüfen (Pellematic Touch Web-Interface erreichbar?)
- Passwort korrekt?
- Firewall-Einstellungen prüfen
- Netzwerk-Verbindung zwischen HA und Pellematic

### Keine Werte bei Sensoren  
```
Sensoren zeigen "Unbekannt" oder JSON-Objekte
```
**Lösung**: 
- Debug-Logs aktivieren
- Integration neu laden
- Parameter-Verfügbarkeit prüfen (nicht alle Parameter bei allen Modellen verfügbar)

### Performance bei vielen Sensoren
```
HA wird langsam bei 80+ Sensoren
```
**Lösung**:
- Debug-Modus deaktivieren für normale Nutzung
- Update-Intervall erhöhen (Standard: 30s)
- Nicht benötigte Sensoren deaktivieren

## 📊 API Details

### Unterstützte Parameter
Die Integration nutzt die ÖkoFen JSON-API mit über 80 Parametern:

**Basis-Parameter**: `CAPPL:FA[0].L_*` (Temperaturen, Status, Laufzeiten)
**Heizkreise**: `CAPPL:LOCAL.L_hk[*].*` (alle HK-Parameter)  
**Warmwasser**: `CAPPL:LOCAL.ww[*].*` und `CAPPL:LOCAL.L_ww[*].*`
**System**: `CAPPL:LOCAL.*` (Fehler, Fernwartung, System-Status)

### Authentifizierung
- Session-basierte Authentifizierung
- Automatische Cookie-Verwaltung
- Sichere Passwort-Speicherung

## 🤝 Mitwirken

Beiträge sind willkommen! 

### Development Setup
```bash
git clone https://github.com/rschnappi/ha-oekofen.git
cd ha-oekofen
# Integration in HA custom_components kopieren
```

### Issues & Feature Requests
- GitHub Issues für Bugs und Feature-Wünsche
- Logs mit Debug-Modus für bessere Diagnose
- ÖkoFen Modell und Firmware-Version angeben

## 📝 Changelog

### v1.8.2 (2024-11-06) - ROBUSTES SESSION-MANAGEMENT 🔒
- **🔐 ENHANCED SESSION MANAGEMENT**:
  - ✅ Automatische Session-Timeout-Erkennung
  - ✅ Transparente Re-Authentication bei Session-Verlust
  - ✅ Robuste Retry-Logic mit HTTP 403/401 Behandlung
  - ✅ Verbesserte Error-Handling für Redirect-Erkennung
  
- **🛡️ STABILITY IMPROVEMENTS**:
  - ✅ Session-Validierung vor allen API-Calls
  - ✅ Intelligente Session-Status-Checks
  - ✅ Reduzierten Session-Ausfälle durch proaktive Re-Auth
  - ✅ Bessere Fehlerbehandlung bei Netzwerkproblemen

- **📊 MAINTAINED FEATURES**:
  - ✅ Alle 80+ Parameter weiterhin verfügbar
  - ✅ Debug-Modus mit vollständiger Systemübersicht
  - ✅ Steuerung & Services funktional
  - ✅ Switch-Entitäten für Warmwasser-Kontrolle

### v1.6.0 (2024-11-05) - MAJOR CONTROL FEATURES 🎛️
- **🎯 VOLLSTÄNDIGE STEUERUNG**: ÖkOfen-Parameter über Home Assistant ändern
- **🔧 5 HOME ASSISTANT SERVICES**:
  - `set_parameter` - Direkte Parameter-Kontrolle 
  - `set_hot_water_mode` - Warmwasser-Modi (Aus/Heizen/Auto)
  - `set_room_temperature` - Raumtemperatur-Sollwerte
  - `set_hot_water_temperature` - Warmwasser-Temperaturen
  - `set_heating_circuit_mode` - Heizkreis-Modi
  
- **🔘 NEUE SWITCH ENTITÄTEN**:
  - Warmwasser Auto-Modus Switch 
  - Einmal-Aufbereitung Switch
  - Zusätzliche Status-Attribute für alle Switches
  
- **🤖 AUTOMATISIERUNG READY**:
  - Service-Calls für komplette Heizungsautomatisierung
  - Beispiel-Automatisierungen für Nachtabsenkung, Anwesenheit
  - Vollständige YAML-Service-Dokumentation

### v1.5.1 (2024-11-05) - CRITICAL CONTEXT FIX 🔧
- **🎯 CONTEXT-AWARE PARAMETER LOADING**: Lösung für fehlende Parameter
- **🔧 DUAL-APPROACH**: Hash-URLs + Parameter-Gruppen Vorladen
- **📊 ALLE 80+ PARAMETER**: Turbine, Asche, Reinigung jetzt verfügbar
- **🚀 ENHANCED WORKFLOW**: Kontext-Besuch vor Parameter-Fetch

### v1.5.0 (2024-11-05) - MAJOR EXPANSION 🔥
- **MASSIV ERWEITERTE PARAMETER-ABDECKUNG**:
  - ✅ Alle fehlenden Heizkreis-Parameter hinzugefügt
  - ✅ Heizkurven (Steigung & Fußpunkt) - Kritische Heizungseinstellungen  
  - ✅ Heizgrenzen (Heizen & Absenken) - Temperaturgrenzen
  - ✅ Vorhaltezeit, Raumfühler Einfluss, Raumtemp Plus
  
- **VOLLSTÄNDIGE WARMWASSER-UNTERSTÜTZUNG**:
  - ✅ Betriebsmodi, Ein-/Ausschalttemperaturen
  - ✅ Zeitprogramme, Pumpen-Status
  - ✅ Alle ww[0].* Parameter implementiert

- **ERWEITERTE SYSTEM-PARAMETER**:
  - ✅ Aschesystem: Schneckendrehzahl, externe Aschebox
  - ✅ Turbine: Vacuum-Zyklen, Reinigungszeiten  
  - ✅ Lüftersystem: Drehzahlen, Unterdruck
  - ✅ Betriebszeiten: Einschub, Pausen, Saugintervalle

- **80+ SENSOR UNTERSTÜTZUNG**:
  - Normal-Modus: ~40-60 Sensoren (je nach Konfiguration)
  - Debug-Modus: 80+ Sensoren mit allen Parametern
  - Strukturierte Datenorganisation mit heating_circuits und hot_water Arrays

### v1.2.0 (2024-11-04)
- ✅ Heizkreis-Sensoren hinzugefügt
- ✅ Konfigurierbare Gerätenamen
- ✅ Erweiterte Wert-Parsing (formatTexts, Timestamps)
- ✅ Session-Management verbessert

### v1.1.0 (2024-11-03)  
- ✅ Cookie-basierte Authentifizierung (CookieJar unsafe=True)
- ✅ JSON-Wert Extraktion repariert
- ✅ Status-Text Parsing (formatTexts)
- ✅ Basis 11-Sensor Implementation

### v1.0.0 (2024-11-02)
- ✅ Erste funktionierende Version
- ✅ ÖkoFen API Integration  
- ✅ Home Assistant Custom Component
- ✅ Config Flow Implementation

## 📄 Lizenz

Dieses Projekt steht unter der MIT Lizenz - siehe [LICENSE](LICENSE) Datei.

## 🔗 Links

- [ÖkoFen Website](https://www.oekofen.com/)
- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)