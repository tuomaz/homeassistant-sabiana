"""Config flow for Sabiana Fan Coil integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_SLAVE_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_SUPPORT_COOLING,
    CONF_SUPPORT_HEATING,
    CONF_MODEL_SCHEMA,
    DEFAULT_PORT,
    DEFAULT_BAUDRATE,
    DEFAULT_SLAVE_ADDRESS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SUPPORT_COOLING,
    DEFAULT_SUPPORT_HEATING,
    DEFAULT_MODEL_SCHEMA,
    LOGGER,
    REG_MODEL,
)
from .hub import SabianaHub

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, str]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = SabianaHub(
        port=data[CONF_PORT],
        baudrate=data[CONF_BAUDRATE],
        slave_address=data[CONF_SLAVE_ADDRESS],
    )
    
    try:
        connected = await hub.connect()
        if not connected:
            raise CannotConnect
        
        # Read the model register to verify slave communication
        await hub.read_holding_registers(REG_MODEL, 1)
    except Exception as err:
        LOGGER.error("Validation failed to connect: %s", err)
        raise CannotConnect from err
    finally:
        await hub.close()

    return {"title": f"Sabiana ({data[CONF_PORT]})"}

class SabianaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sabiana Fan Coil."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): str,
                    vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(
                        [4800, 9600, 19200, 38400, 57600, 115200]
                    ),
                    vol.Required(CONF_SLAVE_ADDRESS, default=DEFAULT_SLAVE_ADDRESS): int,
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                    vol.Required(CONF_SUPPORT_COOLING, default=DEFAULT_SUPPORT_COOLING): bool,
                    vol.Required(CONF_SUPPORT_HEATING, default=DEFAULT_SUPPORT_HEATING): bool,
                    vol.Required(CONF_MODEL_SCHEMA, default=DEFAULT_MODEL_SCHEMA): vol.In(
                        {
                            "auto": "Auto-Detect Model Registers",
                            "schema_a": "Standard (Cassette, Fan Coil, CCP-ECM, Jumbo)",
                            "schema_b": "CVP / QCV (Schema B)",
                        }
                    ),
                }
            ),
            errors=errors,
        )




class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
