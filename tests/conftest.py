"""Shared fixtures for the ÖkOfen platform entity tests."""
from typing import Any, Dict, Optional

import pytest


class FakeCoordinator:
    """Minimal stand-in for DataUpdateCoordinator.

    CoordinatorEntity.__init__ only ever does `self.coordinator = coordinator`
    (verified against the installed homeassistant version), and every entity
    in this integration only reads `coordinator.data` /
    `coordinator.last_update_success` and calls
    `coordinator.async_request_refresh()`. A real DataUpdateCoordinator (and
    therefore a running Home Assistant core / event loop) is not needed to
    exercise the entities' own logic.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, last_update_success: bool = True):
        self.data = data or {}
        self.last_update_success = last_update_success
        self.refresh_calls = 0

    async def async_request_refresh(self) -> None:
        self.refresh_calls += 1


def make_point(
    value: Any,
    divisor: Any = "",
    format_texts: str = "",
    lower_limit: Any = "",
    upper_limit: Any = "",
    status: str = "OK",
) -> Dict[str, Any]:
    """Build a coordinator.data entry shaped like a real PellematicAPI.get_data() item."""
    return {
        "value": value,
        "status": status,
        "divisor": divisor,
        "formatTexts": format_texts,
        "shortText": "",
        "unitText": "",
        "lowerLimit": lower_limit,
        "upperLimit": upper_limit,
    }


@pytest.fixture
def fake_coordinator():
    return FakeCoordinator()
