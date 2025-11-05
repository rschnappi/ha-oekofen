"""Config flow for Ofen integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_LANGUAGE,
    CONF_INTERVAL,
    CONF_DEBUG_MODE,
    DEFAULT_URL,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_LANGUAGE,
    DEFAULT_INTERVAL,
    DEFAULT_DEBUG_MODE,
    DOMAIN,
    LANGUAGE_OPTIONS,
)
from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(LANGUAGE_OPTIONS),
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
        vol.Optional(CONF_DEBUG_MODE, default=DEFAULT_DEBUG_MODE): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = PellematicAPI(
        data[CONF_URL], 
        data[CONF_USERNAME], 
        data[CONF_PASSWORD], 
        data[CONF_LANGUAGE],
        data.get(CONF_DEBUG_MODE, False)
    )
    
    try:
        if not await api.authenticate():
            raise InvalidAuth
        
        # Try to fetch data to ensure full connectivity
        test_data = await api.fetch_data()
        if test_data is None:
            raise CannotConnect
            
    finally:
        await api.close()

    # Return info that you want to store in the config entry.
    return {"title": f"ÖkOfen {data[CONF_URL]}"}


class PlaceholderHub:
    """Placeholder class to represent a hub connection."""

    def __init__(self, url: str, username: str, password: str) -> None:
        """Initialize."""
        self.url = url
        self.username = username
        self.password = password

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        return True


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ofen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""