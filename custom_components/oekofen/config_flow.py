"""Config flow for ÖkOfen Pellematic integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
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
})

class OekofenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ÖkOfen Pellematic."""

    VERSION = 1

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

    async def _test_connection(self, host: str, username: str, password: str) -> bool:
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


class AuthenticationError(Exception):
    """Authentication failed."""
    pass


class ConnectionError(Exception):
    """Connection failed."""
    pass