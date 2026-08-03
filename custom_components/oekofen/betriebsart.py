"""Helpers for resolving the currently-active Heizkreis/Warmwasser Betriebsart slot.

Heizkreis/Warmwasser "betriebsart" is stored on the device as a 3-element
array (betriebsart[0..2]), one slot per possible Anlage-Betriebsart
(Aus/Auto/Warmwasser) - only the slot matching the *current* Anlage mode
is actually live. The vendor's own web UI switches which slot it
reads/writes based on CAPPL:LOCAL.anlage_betriebsart (config.min.js gates
"heizkreis1"/"heizkreis2"/"heizkreis3" on anlage_betriebsart==0/1/2
respectively, each targeting a different betriebsart[N]). Always reading
the fixed betriebsart[0] slot - as this integration did until this fix -
silently shows/controls a stale, inactive slot whenever Anlage isn't
"Aus" (i.e. almost always, since "Auto" is the normal running mode).

Pellematic's betriebsart_fa is NOT slotted this way (single flat
parameter regardless of Anlage mode), so this only applies to hk/ww.
"""
from typing import Any, Dict, List

ANLAGE_MODE_PARAMETER = "CAPPL:LOCAL.anlage_betriebsart"

# The vendor's own UI greys out (aktivierbedingung) the hk/ww Betriebsart
# control while Anlage-Betriebsart == "Aus" (0 is falsy in that JS
# expression) - not a safety gate like the installer PIN, just a UX cue
# that the whole system being off makes per-circuit mode moot until Anlage
# is switched back to Auto/Warmwasser. We keep the field writable (same
# reasoning as the installer-locked fields) but surface the same cue here.
AUS_MODE_HINWEIS = (
    "Anlage-Betriebsart ist aktuell 'Aus' - Änderungen an dieser "
    "Betriebsart wirken sich erst aus, sobald die Anlage wieder auf "
    "Auto/Warmwasser gestellt wird (am Original-Gerät ist dieses Feld in "
    "diesem Zustand ausgegraut)."
)


def active_betriebsart_slot(data: Dict[str, Any]) -> int:
    """Return the array index (0-2) of the currently active betriebsart slot."""
    point = data.get(ANLAGE_MODE_PARAMETER)
    if not point or point.get("value") in (None, ""):
        return 0
    try:
        slot = int(float(point["value"]))
    except (TypeError, ValueError):
        return 0
    return slot if slot in (0, 1, 2) else 0


def betriebsart_parameter(base: str, data: Dict[str, Any]) -> str:
    """Build the currently-active betriebsart[N] parameter string for a hk/ww circuit base."""
    return f"{base}.betriebsart[{active_betriebsart_slot(data)}]"


def betriebsart_slot_parameters(base: str) -> List[str]:
    """All three possible betriebsart[N] parameters for a circuit, for coordinators to poll."""
    return [f"{base}.betriebsart[{slot}]" for slot in (0, 1, 2)]
