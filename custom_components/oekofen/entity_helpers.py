"""Small helpers shared across the ÖkOfen entity platforms.

Every platform builds an identical device-info dict and an identical
"available" check (last_update_success + parameter present in the shared
coordinator's data) - factored out here to avoid repeating the same few
lines in 8+ places, not because either one is complex on its own.
"""
from typing import Any, Dict

from .coordinator import OekofenCoordinator


def build_device_info(entry_id: str, device_name: str) -> Dict[str, Any]:
    """The device-info dict every ÖkOfen entity attaches itself to."""
    return {
        "identifiers": {("oekofen", entry_id)},
        "name": device_name,
        "manufacturer": "ÖkOfen",
        "model": "Pellematic",
    }


def parameter_available(coordinator: OekofenCoordinator, parameter: str) -> bool:
    """Standard availability check: coordinator healthy and this parameter
    was actually returned by the device's last successful poll."""
    return coordinator.last_update_success and parameter in coordinator.data
