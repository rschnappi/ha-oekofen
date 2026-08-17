/**
 * ÖkOfen Pellematic dashboard strategy.
 *
 * Auto-generates a full dashboard from whatever ÖkOfen device/entities are
 * actually registered - no manual PRAEFIX find-and-replace like
 * dashboard_example.yaml, and it scales automatically to however many
 * Heizkreis/Warmwasser/Zirkulationspumpe/Pellematic circuits and time
 * blocks exist on your system.
 *
 * Usage - as the whole dashboard:
 *   strategy:
 *     type: custom:oekofen-strategy
 *
 * Or target a specific device explicitly (useful with multiple ÖkOfen
 * devices in one HA instance):
 *   strategy:
 *     type: custom:oekofen-strategy
 *     device_id: <device id from Settings -> Devices>
 *
 * HOW IT FINDS ENTITIES:
 * Every ÖkOfen entity's entity_id is "<area>_<device name>_<label>", where
 * the "<area>_<device name>_" part is identical for every entity on the
 * device (see README, "Wichtig zu den Entity-IDs"). This strategy derives
 * that shared prefix empirically (longest common prefix across the
 * device's own entity_ids) instead of hardcoding or guessing it, so it
 * keeps working no matter what you've named/arranged the device as. The
 * remaining "<label>" suffix (e.g. "heizkreis_1_betriebsart",
 * "pellematic_1_regeltemperatur_smart") is what gets pattern-matched below
 * - those suffixes come directly from custom_components/oekofen's own
 * German entity names, cross-checked against dashboard_example.yaml.
 */
(function () {
  "use strict";

  const DAYS = [
    "sonntag",
    "montag",
    "dienstag",
    "mittwoch",
    "donnerstag",
    "freitag",
    "samstag",
  ];
  const DAY_LABELS = { sonntag: "So", montag: "Mo", dienstag: "Di", mittwoch: "Mi", donnerstag: "Do", freitag: "Fr", samstag: "Sa" };
  const PROGRAMS = [1, 2];
  const BLOCKS = [1, 2, 3];

  const CIRCUIT_META = {
    heizkreis: { label: "Heizkreis", icon: "mdi:radiator", emoji: "\u{1F3E0}", hasZeitprogramm: true, hasClimate: true },
    warmwasser: { label: "Warmwasser", icon: "mdi:water-boiler", emoji: "\u{1F4A7}", hasZeitprogramm: true, hasClimate: true },
    pellematic: { label: "Pellematic", icon: "mdi:fire", emoji: "\u{1F525}", hasZeitprogramm: false, hasClimate: true },
    zirkulationspumpe: { label: "Zirkulationspumpe", icon: "mdi:pump", emoji: "\u{1F504}", hasZeitprogramm: true, hasClimate: false },
  };

  function domainOf(entityId) {
    return entityId.slice(0, entityId.indexOf("."));
  }

  function objectIdOf(entityId) {
    return entityId.slice(entityId.indexOf(".") + 1);
  }

  /** Longest common prefix across all object_ids, trimmed back to the last "_". */
  function commonPrefix(objectIds) {
    if (!objectIds.length) return "";
    let prefix = objectIds[0];
    for (let i = 1; i < objectIds.length; i++) {
      const s = objectIds[i];
      let j = 0;
      const max = Math.min(prefix.length, s.length);
      while (j < max && prefix[j] === s[j]) j++;
      prefix = prefix.slice(0, j);
      if (!prefix) break;
    }
    const cut = prefix.lastIndexOf("_");
    return cut >= 0 ? prefix.slice(0, cut + 1) : "";
  }

  /**
   * Group a device's entity_ids into { prefix, bySuffix, circuits, leftover }.
   * bySuffix maps "domain:suffix" -> entity_id.
   * circuits maps "type_index" (e.g. "heizkreis_1") -> { type, index, entities: {suffixKey: entityId} }
   */
  function analyzeEntities(entityIds) {
    const objectIds = entityIds.map(objectIdOf);
    const prefix = commonPrefix(objectIds);

    const bySuffix = new Map();
    const claimed = new Set();
    entityIds.forEach((entityId, i) => {
      const suffix = objectIds[i].startsWith(prefix) ? objectIds[i].slice(prefix.length) : objectIds[i];
      bySuffix.set(`${domainOf(entityId)}:${suffix}`, entityId);
    });

    const circuitRe = /^(heizkreis|warmwasser|pellematic|zirkulationspumpe)_(\d+)(?:_(.*))?$/;
    const circuits = new Map();
    for (const key of bySuffix.keys()) {
      const suffix = key.slice(key.indexOf(":") + 1);
      const m = suffix.match(circuitRe);
      if (!m) continue;
      const [, type, index] = m;
      const circuitKey = `${type}_${index}`;
      if (!circuits.has(circuitKey)) {
        circuits.set(circuitKey, { type, index: Number(index), suffix: `${type}_${index}`, entities: new Map() });
      }
    }

    // Sort circuit keys for stable, numeric-aware ordering (heizkreis_1, heizkreis_2, ... pellematic_1, ...)
    const orderedTypes = ["heizkreis", "warmwasser", "pellematic", "zirkulationspumpe"];
    const circuitList = Array.from(circuits.values()).sort((a, b) => {
      const ta = orderedTypes.indexOf(a.type);
      const tb = orderedTypes.indexOf(b.type);
      return ta !== tb ? ta - tb : a.index - b.index;
    });

    for (const circuit of circuitList) {
      const circuitPrefix = `${circuit.suffix}_`;
      for (const [key, entityId] of bySuffix.entries()) {
        const [domain, suffix] = [key.slice(0, key.indexOf(":")), key.slice(key.indexOf(":") + 1)];
        let relative = null;
        if (suffix === circuit.suffix) relative = "";
        else if (suffix.startsWith(circuitPrefix)) relative = suffix.slice(circuitPrefix.length);
        if (relative !== null) {
          circuit.entities.set(`${domain}:${relative}`, entityId);
          claimed.add(key);
        }
      }
    }

    const leftover = [];
    for (const [key, entityId] of bySuffix.entries()) {
      if (!claimed.has(key)) leftover.push(entityId);
    }
    leftover.sort();

    return { prefix, bySuffix, circuits: circuitList, leftover };
  }

  function tile(entity, name, icon) {
    const card = { type: "tile", entity };
    if (name) card.name = name;
    if (icon) card.icon = icon;
    return card;
  }

  function grid(cards, columns) {
    return { type: "grid", columns: columns || 2, square: false, cards };
  }

  function markdown(content) {
    return { type: "markdown", content };
  }

  function stack(cards) {
    return { type: "vertical-stack", cards };
  }

  /** All entities of a circuit under a given domain, sorted by entity_id (stable, no hardcoded catalog). */
  function domainEntities(circuit, domain) {
    const out = [];
    for (const [key, entityId] of circuit.entities.entries()) {
      if (key.startsWith(`${domain}:`)) out.push(entityId);
    }
    out.sort();
    return out;
  }

  function circuitEntity(circuit, domain, suffix) {
    return circuit.entities.get(`${domain}:${suffix}`) || null;
  }

  /** Settings grid: every number/select entity of the circuit not already used elsewhere. */
  function buildSettingsGrid(circuit, usedEntityIds) {
    const used = new Set(usedEntityIds.filter(Boolean));
    const cards = [];
    for (const domain of ["number", "select"]) {
      for (const entityId of domainEntities(circuit, domain)) {
        if (used.has(entityId)) continue;
        // Zeitprogramm/day-schedule entities are handled in their own section.
        const suffix = entityId.slice(entityId.indexOf(".") + 1);
        if (/_zeit_\d+_/.test(suffix)) continue;
        cards.push(tile(entityId));
      }
    }
    return cards;
  }

  function buildZeitprogrammSection(circuit) {
    const cards = [markdown(`## \u{1F552} Zeitprogramme - ${CIRCUIT_META[circuit.type].label} ${circuit.index}`)];
    for (const program of PROGRAMS) {
      const dayTiles = [];
      const timeEntities = [];
      let anyFound = false;
      for (const day of DAYS) {
        const switchEntity = circuitEntity(circuit, "switch", `zeit_${program}_${day}_aktiv`);
        if (switchEntity) {
          anyFound = true;
          dayTiles.push(tile(switchEntity, DAY_LABELS[day], "mdi:calendar-check"));
        }
        for (const block of BLOCKS) {
          const von = circuitEntity(circuit, "time", `zeit_${program}_${day}_block_${block}_von`);
          const bis = circuitEntity(circuit, "time", `zeit_${program}_${day}_block_${block}_bis`);
          if (von) timeEntities.push({ entity: von, name: `${DAY_LABELS[day]} Block ${block} Von`, icon: "mdi:clock-start" });
          if (bis) timeEntities.push({ entity: bis, name: `${DAY_LABELS[day]} Block ${block} Bis`, icon: "mdi:clock-end" });
        }
      }
      if (!anyFound) continue;
      const programCards = [markdown(`### Zeit ${program}`), grid(dayTiles, 7)];
      if (timeEntities.length) {
        programCards.push({ type: "entities", entities: timeEntities });
      }
      cards.push(stack(programCards));
    }
    return cards.length > 1 ? [stack(cards)] : [];
  }

  function buildCircuitView(circuit) {
    const meta = CIRCUIT_META[circuit.type];
    const title = `${meta.label} ${circuit.index}`;
    const usedForSettings = [];
    const topCards = [];

    if (meta.hasClimate) {
      const climateEntity = circuitEntity(circuit, "climate", "");
      if (climateEntity) {
        topCards.push(markdown(`## ${meta.emoji} ${title}`));
        topCards.push({ type: "thermostat", entity: climateEntity });
        usedForSettings.push(climateEntity);
      }
    }
    const modeSelect = circuitEntity(circuit, "select", "betriebsart");
    if (modeSelect) usedForSettings.push(modeSelect);
    const zeitprogrammSelect = circuitEntity(circuit, "select", "aktives_zeitprogramm");
    if (zeitprogrammSelect) usedForSettings.push(zeitprogrammSelect);

    const quickCards = [];
    if (!topCards.length) {
      topCards.push(markdown(`## ${title}`));
    }
    if (modeSelect) quickCards.push(tile(modeSelect, "Betriebsart"));
    if (zeitprogrammSelect) quickCards.push(tile(zeitprogrammSelect, "Zeitprogramm"));
    if (quickCards.length) topCards.push(grid(quickCards, 2));

    const cardStacks = [stack(topCards)];

    const settingsCards = buildSettingsGrid(circuit, usedForSettings);
    if (settingsCards.length) {
      cardStacks.push(stack([markdown(`## ⚙️ Einstellungen ${title}`), grid(settingsCards, 2)]));
    }

    // Party/Urlaub (Heizkreis) and Einmal Aufbereiten (Warmwasser), if present.
    const extraCards = [];
    for (const [suffix, name, icon] of [
      ["partyprogramm", "Party aktiv", "mdi:party-popper"],
      ["party_endzeit", "Party Endzeit", "mdi:clock-end"],
      ["urlaubsprogramm", "Urlaub aktiv", "mdi:airplane"],
      ["urlaub_start", "Urlaub Start", "mdi:airplane-takeoff"],
      ["urlaub_ende", "Urlaub Ende", "mdi:airplane-landing"],
      ["einmal_aufbereiten", "Einmal Aufbereiten", "mdi:water-boiler-auto"],
      ["vorrang", "Vorrang", "mdi:priority-high"],
      ["legionellenschutz", "Legionellenschutz", "mdi:shield-check"],
    ]) {
      const entityId =
        circuitEntity(circuit, "switch", suffix) ||
        circuitEntity(circuit, "datetime", suffix) ||
        circuitEntity(circuit, "select", suffix);
      if (entityId) {
        extraCards.push(tile(entityId, name, icon));
        usedForSettings.push(entityId);
      }
    }
    if (extraCards.length) {
      cardStacks.push(stack([markdown("## \u{1F389} Party / Urlaub"), grid(extraCards, 2)]));
    }

    if (meta.hasZeitprogramm) {
      cardStacks.push(...buildZeitprogrammSection(circuit));
    }

    return {
      title,
      path: circuit.suffix.replace(/_/g, "-"),
      icon: meta.icon,
      cards: cardStacks,
    };
  }

  function buildOverviewView(circuits, leftoverEntityIds, hass) {
    const cards = [];
    const modeCards = [];
    for (const circuit of circuits) {
      const modeSelect = circuitEntity(circuit, "select", "betriebsart");
      const climateEntity = circuitEntity(circuit, "climate", "");
      const entity = modeSelect || climateEntity;
      if (entity) {
        modeCards.push(tile(entity, `${CIRCUIT_META[circuit.type].label} ${circuit.index}`, CIRCUIT_META[circuit.type].icon));
      }
    }
    if (modeCards.length) {
      cards.push(stack([markdown("## \u{1F527} Betriebsarten"), grid(modeCards, 2)]));
    }

    if (leftoverEntityIds.length) {
      const bySensorDomain = new Map();
      for (const entityId of leftoverEntityIds) {
        const d = domainOf(entityId);
        if (!bySensorDomain.has(d)) bySensorDomain.set(d, []);
        bySensorDomain.get(d).push(entityId);
      }
      const domainTitles = {
        sensor: "\u{1F321}️ Sensoren & Diagnose",
        select: "\u{1F39B}️ Weitere Betriebsarten",
        number: "⚙️ Weitere Einstellungen",
        switch: "\u{1F50C} Weitere Schalter",
        text: "\u{1F4E7} Mail / SMTP",
        datetime: "\u{1F552} Datum & Uhrzeit",
      };
      for (const [domain, ids] of bySensorDomain.entries()) {
        cards.push(
          stack([markdown(`## ${domainTitles[domain] || domain}`), { type: "entities", entities: ids.map((e) => ({ entity: e })) }])
        );
      }
    }

    return { title: "Übersicht", path: "overview", icon: "mdi:home-thermometer", cards };
  }

  class OekofenStrategy {
    static async generate(config, hass) {
      const devices = Object.values(hass.devices || {});
      let targetDevices = devices.filter((d) => d.manufacturer === "ÖkOfen" && d.model === "Pellematic");
      if (config && config.device_id) {
        targetDevices = devices.filter((d) => d.id === config.device_id);
      }

      if (!targetDevices.length) {
        return {
          views: [
            {
              title: "ÖkOfen",
              cards: [
                markdown(
                  "## Kein ÖkOfen-Gerät gefunden\n\nPrüfe, ob die ha-oekofen-Integration eingerichtet ist, oder gib in der Strategy-Konfiguration explizit `device_id` an."
                ),
              ],
            },
          ],
        };
      }

      const allEntities = Object.values(hass.entities || {});
      const views = [];
      const multipleDevices = targetDevices.length > 1;

      for (const device of targetDevices) {
        const entityIds = allEntities.filter((e) => e.device_id === device.id).map((e) => e.entity_id);
        const { circuits, leftover } = analyzeEntities(entityIds);
        const deviceLabel = device.name_by_user || device.name || device.id;
        const deviceSlug = String(deviceLabel).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

        const deviceViews = [buildOverviewView(circuits, leftover, hass), ...circuits.map(buildCircuitView)];
        if (multipleDevices) {
          for (const view of deviceViews) {
            view.title = `${deviceLabel}: ${view.title}`;
            view.path = `${deviceSlug}-${view.path}`;
          }
        }
        views.push(...deviceViews);
      }

      return { views };
    }
  }

  if (typeof customElements !== "undefined" && !customElements.get("ll-strategy-dashboard-oekofen")) {
    customElements.define("ll-strategy-dashboard-oekofen", OekofenStrategy);
  }

  if (typeof window !== "undefined") {
    window.customCards = window.customCards || [];
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { OekofenStrategy, analyzeEntities, commonPrefix, objectIdOf, domainOf };
  }
})();
