# ÖkoFen Pellematic Smart XS Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/rschnappi/ha-oekofen.svg)](https://github.com/rschnappi/ha-oekofen/releases)
[![License](https://img.shields.io/github/license/rschnappi/ha-oekofen.svg)](LICENSE)

Eine umfassende Home Assistant Custom Component für ÖkoFen Pellematic Smart XS Pelletkessel.

## 🔥 Features

- **Vollständige API-Integration** mit ÖkoFen Pellematic Steuerung
- **80+ Sensoren** für komplette Systemüberwachung
- **Erweiterte Heizkurven-Parameter** (Steigung, Fußpunkt, Heizgrenzen)
- **Warmwasser-Kreislauf Überwachung** mit allen Temperaturen und Modi
- **Aschesystem-Monitoring** inkl. Schneckendrehzahl und externe Aschebox
- **Turbinen- und Reinigungssystem** Parameter
- **Debug-Modus** mit allen verfügbaren Parametern
- **Konfigurierbare Gerätenamen** über UI
- **Automatische Wert-Parsing** (formatTexts, Timestamps, Divisoren)

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