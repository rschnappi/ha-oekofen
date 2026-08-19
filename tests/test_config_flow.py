"""Tests for config_flow.py's reauthentication flow.

async_step_reauth/async_step_reauth_confirm are what HA calls after
ConfigEntryAuthFailed is raised (see __init__.py's async_setup_entry and
coordinator.py's _async_update_data) - without them, a bad/changed
technician password would leave the entry failed or entities unavailable
with no way for the user to fix it short of removing and re-adding the
whole integration.

ConfigFlow can be constructed standalone (FlowHandler.__init__ needs no
hass/flow-manager setup) - _get_reauth_entry()/async_update_reload_and_abort()
are stubbed directly rather than going through a real flow manager, matching
the "test the logic, not the HA plumbing" style used throughout this repo's
other tests.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.oekofen.config_flow import (
    AuthenticationError,
    ConnectionError as OekofenConnectionError,
    OekofenConfigFlow,
)


def _make_flow(entry_data):
    flow = OekofenConfigFlow()
    flow.hass = MagicMock()
    entry = MagicMock()
    entry.data = entry_data
    flow._get_reauth_entry = MagicMock(return_value=entry)
    flow.async_update_reload_and_abort = MagicMock(
        return_value={"type": "abort", "reason": "reauth_successful"}
    )
    return flow, entry


async def test_reauth_step_delegates_to_confirm():
    flow, _entry = _make_flow({"host": "1.2.3.4", "username": "u", "password": "old"})
    with patch.object(
        OekofenConfigFlow, "async_step_reauth_confirm", AsyncMock(return_value="confirm-result")
    ) as mock_confirm:
        result = await flow.async_step_reauth({})

    mock_confirm.assert_awaited_once()
    assert result == "confirm-result"


async def test_reauth_confirm_shows_form_with_no_errors_on_first_call():
    flow, _entry = _make_flow({"host": "1.2.3.4", "username": "u", "password": "old", "language": "de"})
    result = await flow.async_step_reauth_confirm()
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}


async def test_reauth_confirm_success_updates_entry_and_reloads():
    flow, entry = _make_flow({"host": "1.2.3.4", "username": "u", "password": "old", "language": "de"})
    with patch.object(OekofenConfigFlow, "_test_connection", AsyncMock(return_value=True)):
        await flow.async_step_reauth_confirm(
            {"host": "1.2.3.4", "username": "u", "password": "new", "language": "de"}
        )

    flow.async_update_reload_and_abort.assert_called_once()
    (updated_entry,), kwargs = flow.async_update_reload_and_abort.call_args
    assert updated_entry is entry
    assert kwargs["data"]["password"] == "new"


async def test_reauth_confirm_invalid_auth_shows_error_and_does_not_update_entry():
    flow, _entry = _make_flow({"host": "1.2.3.4", "username": "u", "password": "old", "language": "de"})
    with patch.object(
        OekofenConfigFlow, "_test_connection", AsyncMock(side_effect=AuthenticationError("nope"))
    ):
        result = await flow.async_step_reauth_confirm(
            {"host": "1.2.3.4", "username": "u", "password": "wrong", "language": "de"}
        )

    assert result["errors"] == {"base": "invalid_auth"}
    flow.async_update_reload_and_abort.assert_not_called()


async def test_reauth_confirm_connection_error_shows_error():
    flow, _entry = _make_flow({"host": "1.2.3.4", "username": "u", "password": "old", "language": "de"})
    with patch.object(
        OekofenConfigFlow, "_test_connection", AsyncMock(side_effect=OekofenConnectionError("down"))
    ):
        result = await flow.async_step_reauth_confirm(
            {"host": "1.2.3.4", "username": "u", "password": "old", "language": "de"}
        )

    assert result["errors"] == {"base": "cannot_connect"}
    flow.async_update_reload_and_abort.assert_not_called()
