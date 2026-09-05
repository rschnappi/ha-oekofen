# ÖkOfen: Anlage automatisch für Wartungstermine ausschalten

Drei zusammengehörige Blueprints, die die Anlage (oder einen einzelnen
Heizkreis/Warmwasser) am Abend vor einem Wartungstermin ("Rauchfangkehrer",
"Service Ofen", ...) automatisch ausschalten, damit der Kessel kalt ist -
und danach mit einem Tastendruck wieder auf den vorherigen Zustand
zurückstellen.

Das Feature braucht **keine Änderung an der Integration selbst** - es nutzt
nur Entities, die `ha-oekofen` ohnehin bereitstellt (z. B.
`select.<bereich>_<gerät>_anlage_betriebsart`), plus Bordmittel von Home
Assistant (Kalender, Szenen, Benachrichtigungs-Aktionen).

## Ablauf

1. **"ÖkOfen: Anlage vor Wartungstermin ausschalten"** prüft täglich zu einer
   festgelegten Uhrzeit (Default 20:00), ob im gewählten Kalender am
   nächsten Tag ein Termin mit einem der konfigurierten Stichworte steht.
   Falls ja: aktuellen Zustand der gewählten Betriebsart-Entity in einer
   Szene sichern, Entity auf "Aus" schalten, Benachrichtigung schicken.
2. **"ÖkOfen: Erinnerung nach Wartungstermin"** schickt nach Ende des
   Termins eine Benachrichtigung mit einem Aktions-Button "Zurückstellen".
3. **"ÖkOfen: Auf Vor-Wartungszustand zurückstellen"** reagiert auf den
   Button-Tap und aktiviert die gesicherte Szene wieder.

## Voraussetzungen

- Ein Kalender in Home Assistant, in den der Wartungstermin eingetragen
  wird - am einfachsten die eingebaute **"Lokaler Kalender"**-Integration
  (Einstellungen → Geräte & Dienste → Integration hinzufügen → "Lokaler
  Kalender").
- Ein `notify.*`-Ziel, üblicherweise die Companion-App eines Handys
  (Einstellungen → Geräte & Dienste → Mobile App).
- Die zu schaltende `select`-Entity deiner Anlage, z. B.
  `select.heizraum_ofen_anlage_betriebsart` (gesamte Anlage) oder eine
  einzelne Heizkreis-/Warmwasser-Betriebsart, falls nur ein Teil
  ausgeschaltet werden soll.

## Installation

### Import per URL (empfohlen)

Für jedes der drei Blueprints in Home Assistant: **Einstellungen →
Automatisierungen & Szenen → Blueprints → Blueprint importieren**, dann die
Raw-URL der jeweiligen Datei einfügen:

- `https://github.com/rschnappi/ha-oekofen/blob/main/blueprints/automation/oekofen/wartung_vorbereiten.yaml`
- `https://github.com/rschnappi/ha-oekofen/blob/main/blueprints/automation/oekofen/wartung_erinnerung.yaml`
- `https://github.com/rschnappi/ha-oekofen/blob/main/blueprints/automation/oekofen/wartung_zuruecksetzen.yaml`

### Manuell kopieren

Alternativ die drei `.yaml`-Dateien aus diesem Ordner nach
`<config>/blueprints/automation/oekofen/` kopieren und die Blueprint-Seite
neu laden.

## Automatisierungen anlegen

Nach dem Import für jedes der drei Blueprints über **Automatisierung
erstellen → Aus Blueprint** eine Automatisierung anlegen und die Felder
ausfüllen.

**Wichtig - diese Werte müssen zwischen den Automatisierungen exakt
übereinstimmen:**

| Feld | in Blueprint 1 | in Blueprint 2 | in Blueprint 3 |
|---|---|---|---|
| Kalender | ✅ | ✅ | - |
| Termin-Stichworte | ✅ | ✅ | - |
| Szenen-ID | ✅ (erzeugt `scene.<szenen-id>`) | - | ✅ (muss dieselbe `scene.<szenen-id>` referenzieren) |
| Aktions-ID | - | ✅ | ✅ (muss identisch sein) |

### Beispielkonfiguration

- Kalender: `calendar.ofen_wartung` (aus "Lokaler Kalender", Name z. B.
  "Ofen Wartung")
- Betriebsart-Entity: `select.heizraum_ofen_anlage_betriebsart`
- Termin-Stichworte: `Rauchfangkehrer, Service Ofen`
- Szenen-ID: `oekofen_zustand_vor_wartung`
- Aktions-ID: `OEKOFEN_RESTORE_ANLAGE`
- Benachrichtigung: `notify.<dein_handy>`

Trage den Termin dann einfach mit exakt einem der konfigurierten Stichworte
(z. B. "Rauchfangkehrer") im Kalender ein - der Rest läuft automatisch.

## Hinweise

- Der Kalendertitel muss (nach Trimmen und Groß-/Kleinschreibung) einem der
  Stichworte entsprechen, sonst greift die Erkennung nicht.
- Die Szene sichert nur die eine ausgewählte Entity. Sollen mehrere Kreise
  gesichert werden, mehrere Entities in einer eigenen, angepassten
  Automatisierung snapshotten (die Blueprints unterstützen aktuell eine
  Entity pro Instanz - für "die ganze Anlage" reicht in der Regel die
  übergeordnete Anlage-Betriebsart-Entity).
- Getestet gegen eine echte ÖkOfen-Instanz (Szene sichern → Anlage aus →
  Szene wiederherstellen, inklusive realer Geräte-Rundlaufzeit).
