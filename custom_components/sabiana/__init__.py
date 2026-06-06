"""The Sabiana Fan Coil integration."""
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_SLAVE_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_MODEL_SCHEMA,
    LOGGER,
)
from .hub import SabianaHub

PLATFORMS = ["climate", "sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sabiana Fan Coil from a config entry."""
    port = entry.data[CONF_PORT]
    baudrate = entry.data[CONF_BAUDRATE]
    slave_address = entry.data[CONF_SLAVE_ADDRESS]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    model_schema = entry.data.get(CONF_MODEL_SCHEMA, "auto")

    hub = SabianaHub(port, baudrate, slave_address, model_schema)
    
    # Try initial connection
    connected = await hub.connect()
    if not connected:
        LOGGER.error("Failed to connect to Sabiana Modbus on %s", port)
        raise ConfigEntryNotReady(f"Failed to connect to Sabiana Modbus on {port}")

    # Auto-detect or load the registered schema configuration
    await hub.detect_schema()


    async def async_update_data() -> dict:
        """Fetch data from Modbus."""
        try:
            return await hub.async_update_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Sabiana unit: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["hub"].close()

    return unload_ok
