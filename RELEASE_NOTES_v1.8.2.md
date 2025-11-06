# ÖkoFen Integration v1.8.2 - Robustes Session-Management

## 🎯 **Neuerungen in v1.8.2:**

### 🔒 **Robustes Session-Management**
- **Automatische Session-Timeout-Erkennung** - Erkennt abgelaufene Sessions proaktiv
- **Transparente Re-Authentication** - Automatische Neu-Anmeldung ohne Nutzer-Intervention
- **Intelligente Retry-Logic** - Wiederholung bei temporären Verbindungsproblemen
- **Verbesserte Error-Behandlung** - Robuste Behandlung von HTTP 403/401 und Redirects

### 🛡️ **Stabilität & Zuverlässigkeit**
- **Session-Validierung** vor allen API-Aufrufen
- **Proaktive Re-Authentication** verhindert Session-Ausfälle
- **Bessere Netzwerk-Fehlerbehandlung** für instabile Verbindungen
- **Reduzierte manuelle Neustarts** der Integration

### 📊 **Beibehaltene Features**
- ✅ **80+ Sensoren** für komplette Systemüberwachung
- ✅ **5 Home Assistant Services** für Heizungssteuerung
- ✅ **Switch-Entitäten** für Warmwasser-Kontrolle
- ✅ **Debug-Modus** mit allen verfügbaren Parametern
- ✅ **Automatisierungs-Support** für intelligente Heizungsregelung

## 🔧 **Technische Verbesserungen**

### Session-Management-Methoden:
```python
async def _check_session_valid() -> bool
async def _ensure_authenticated() -> bool
# Verbesserte fetch_data() und set_parameter() mit Retry-Logic
```

### Verbesserte Fehlerbehandlung:
- **HTTP 403/401 Detection** → Automatische Re-Authentication
- **Redirect-Erkennung** → Session-Invalidierung und Neuanmeldung
- **Timeout-Behandlung** → Graceful Retry-Mechanismen

## 🚀 **Installation & Upgrade**

### HACS Installation:
1. HACS → Integrationen → "ÖkoFen Pellematic"
2. Version v1.8.2 installieren
3. Home Assistant neu starten
4. Integration funktioniert automatisch stabiler

### Manuelle Installation:
1. `custom_components/ofen` Ordner aktualisieren
2. Home Assistant neu starten
3. Bestehende Konfiguration bleibt erhalten

## 💡 **Nutzer-Erfahrung**

**Vorher (v1.8.1):**
- Session-Timeouts erfordern manuelle Neustarts
- Verbindungsabbrüche führen zu "Unbekannt"-Werten
- Instabile Datenerfassung bei Netzwerkproblemen

**Nachher (v1.8.2):**
- ✅ Automatische Session-Wiederherstellung
- ✅ Kontinuierliche Datenerfassung auch bei Timeout
- ✅ Stabile Verbindung ohne manuelle Eingriffe
- ✅ Robuste Performance bei Netzwerkproblemen

## 🛠️ **Breaking Changes**
**Keine** - Die Konfiguration bleibt vollständig kompatibel.

---

**Diese Version fokussiert auf Stabilität und Zuverlässigkeit - die Basis für zukünftige Feature-Erweiterungen.** 🔒