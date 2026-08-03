"""Config flow for ÖkOfen Pellematic integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .pellematic_api import PellematicAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oekofen"

# Configuration schema
DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required("language", default="de"): vol.In(["de", "en", "fr", "it"]),
})

class OekofenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ÖkOfen Pellematic."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "OekofenOptionsFlow":
        """Get the options flow, used to edit host/credentials after setup."""
        return OekofenOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Test the connection with provided credentials
                await self._test_connection(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD]
                )
                
                # Create the config entry
                return self.async_create_entry(
                    title=f"ÖkOfen {user_input[CONF_HOST]}",
                    data=user_input
                )
                
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"

        # Show the configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "host_example": "http://192.168.1.100"
            }
        )

    @staticmethod
    async def _test_connection(host: str, username: str, password: str) -> bool:
        """Test the connection to the ÖkOfen device."""
        # Ensure URL format
        if not host.startswith(('http://', 'https://')):
            host = f"http://{host}"
        
        try:
            async with PellematicAPI(host, username, password) as api:
                # Test authentication
                if not await api.authenticate():
                    raise AuthenticationError("Authentication failed")
                
                # Test data retrieval with a simple parameter
                test_data = await api.get_data(["CAPPL:LOCAL.L_aussentemperatur_ist"])
                
                if not test_data:
                    raise ConnectionError("No data received from device")
                
                _LOGGER.info("Connection test successful")
                return True
                
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            if "authentication" in str(e).lower():
                raise AuthenticationError(str(e))
            else:
                raise ConnectionError(str(e))


class OekofenOptionsFlow(config_entries.OptionsFlow):
    """Let the user edit host/credentials/language of an existing entry.

    Without this, changing the device's IP address or the technician
    login required removing and re-adding the whole integration (losing
    entity history/customizations). The result is written back into the
    entry's main data (not a separate "options" dict) so the rest of the
    integration keeps reading it via entry.data as before; the existing
    update listener (see __init__.py) reloads the entry afterwards.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        errors = {}
        current = self.config_entry.data

        if user_input is not None:
            try:
                await OekofenConfigFlow._test_connection(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=user_input,
                    title=f"ÖkOfen {user_input[CONF_HOST]}",
                )
                return self.async_create_entry(title="", data={})
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error updating ÖkOfen options")
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=current.get(CONF_HOST)): cv.string,
            vol.Required(CONF_USERNAME, default=current.get(CONF_USERNAME)): cv.string,
            vol.Required(CONF_PASSWORD, default=current.get(CONF_PASSWORD)): cv.string,
            vol.Required("language", default=current.get("language", "de")): vol.In(["de", "en", "fr", "it"]),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


class AuthenticationError(Exception):
    """Authentication failed."""
    pass


class ConnectionError(Exception):
    """Connection failed."""
    pass