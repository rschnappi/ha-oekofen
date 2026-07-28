"""Discover which circuits/units are actually present on the ÖkOfen device.

The device supports up to 6 heating circuits, 3 hot-water circuits, 3
circulation pumps and 4 Pellematic boiler units - but almost every
installation only has one or two of each. Probing the "vorhanden"
(present) flags once at startup lets every other platform only create
entities for hardware that actually exists, instead of guessing.
"""
import logging
from typing import Dict, List

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

MAX_HK = 6
MAX_WW = 3
MAX_ZIRKP = 3
MAX_PELLEMATIC = 4

# Fallback used if discovery fails for some reason - matches the most
# common single-boiler / single-heating-circuit installation so the
# integration still comes up with something useful.
FALLBACK_CIRCUITS = {"hk": [0], "ww": [0], "zirkp": [], "pellematic": [0]}


async def async_discover_circuits(api: PellematicAPI) -> Dict[str, List[int]]:
    """Probe the device and return which circuit indices exist."""
    probe_params = []
    probe_params += [f"CAPPL:LOCAL.hk[{i}].vorhanden" for i in range(MAX_HK)]
    probe_params += [f"CAPPL:LOCAL.ww[{i}].vorhanden" for i in range(MAX_WW)]
    probe_params += [f"CAPPL:LOCAL.zirkp[{i}].vorhanden" for i in range(MAX_ZIRKP)]
    probe_params += [f"CAPPL:LOCAL.pellematic_vorhanden[{i}]" for i in range(MAX_PELLEMATIC)]

    try:
        data = await api.get_data(probe_params)
    except Exception as err:  # noqa: BLE001 - discovery must never hard-fail setup
        _LOGGER.warning(
            "Circuit discovery failed (%s), falling back to hk[0]/ww[0]/pellematic[0]",
            err,
        )
        return dict(FALLBACK_CIRCUITS)

    def _present(name: str) -> bool:
        point = data.get(name)
        if not point:
            return False
        try:
            return int(float(point.get("value"))) == 1
        except (TypeError, ValueError):
            return False

    circuits = {
        "hk": [i for i in range(MAX_HK) if _present(f"CAPPL:LOCAL.hk[{i}].vorhanden")],
        "ww": [i for i in range(MAX_WW) if _present(f"CAPPL:LOCAL.ww[{i}].vorhanden")],
        "zirkp": [i for i in range(MAX_ZIRKP) if _present(f"CAPPL:LOCAL.zirkp[{i}].vorhanden")],
        "pellematic": [
            i for i in range(MAX_PELLEMATIC) if _present(f"CAPPL:LOCAL.pellematic_vorhanden[{i}]")
        ],
    }

    if not any(circuits.values()):
        _LOGGER.warning("Circuit discovery found nothing present, using fallback")
        return dict(FALLBACK_CIRCUITS)

    _LOGGER.info("Discovered ÖkOfen circuits: %s", circuits)
    return circuits
