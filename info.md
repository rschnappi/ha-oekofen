# ÖkOfen Pellematic Integration

Diese Integration ermöglicht es, ÖkOfen Pellematic Heizsysteme in Home Assistant zu integrieren.

## Installation über HACS

1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf "Integrationen"  
3. Klicken Sie auf die drei Punkte oben rechts und wählen Sie "Benutzerdefinierte Repositories"
4. Fügen Sie diese Repository-URL hinzu: `https://github.com/rschnappi/ha-oekofen`
5. Wählen Sie "Integration" als Kategorie
6. Installieren Sie die Integration
7. Starten Sie Home Assistant neu
8. Fügen Sie die Integration über Einstellungen → Geräte & Services hinzu

## Konfiguration

Geben Sie folgende Informationen ein:
- **URL**: Die URL Ihres Pellematic Systems (z.B. http://192.168.1.100)
- **Benutzername**: Ihr Login-Benutzername  
- **Passwort**: Ihr Login-Passwort
- **Sprache**: de oder en
- **Update-Intervall**: 5-3600 Sekunden
- **Debug-Modus**: Optional für Entwicklung/Debugging

## Funktionen

- Überwachung von Außentemperatur, Kesseltemperaturen und Pufferspeicher
- Anzeige des Kesselstatus und Fehlerzählers
- Pumpenstatus-Überwachung
- Mehrsprachige Unterstützung
- Konfigurierbare Update-Intervalle

Die Integration nutzt die gleichen API-Endpunkte wie die originale ÖkOfen Web-Oberfläche.