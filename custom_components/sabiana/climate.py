"""Support for Sabiana Climate entity."""
from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_SUPPORT_COOLING,
    CONF_SUPPORT_HEATING,
    REG_T1,
    REG_MACHINE_STATE,
    REG_FAN_ONLY_MODE,
    REG_AUTO_MODE,
    REG_SEASON_IN_USE,
    REG_AUTO_VENT,
    REG_FAN_MIN_STATE,
    REG_FAN_MED_STATE,
    REG_FAN_MAX_STATE,
    REG_SUMMER_SETPOINT,
    REG_WINTER_SETPOINT,
    LOGGER,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sabiana Climate platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub = data["hub"]
    coordinator = data["coordinator"]

    async_add_entities([SabianaClimate(coordinator, hub, entry)], True)

class SabianaClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Sabiana Fan Coil Climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 10.0
    _attr_max_temp = 30.0

    _attr_fan_modes = ["auto", "low", "medium", "high"]

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
    )

    def __init__(self, coordinator, hub, entry) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._hub = hub
        self._entry = entry
        
        self._support_cooling = entry.data.get(CONF_SUPPORT_COOLING, True)
        self._support_heating = entry.data.get(CONF_SUPPORT_HEATING, True)

        # Build hvac modes dynamically based on capabilities configured
        modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
        if self._support_cooling:
            modes.append(HVACMode.COOL)
        if self._support_heating:
            modes.append(HVACMode.HEAT)
        if self._support_cooling and self._support_heating:
            modes.append(HVACMode.AUTO)
        
        self._attr_hvac_modes = modes

        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sabiana Fan Coil",
            manufacturer="Sabiana",
            model="Carisma Fly CVP-ECM-MB",
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current ambient temperature."""
        temp = self.coordinator.data.get(REG_T1)
        if temp is not None:
            # The register value is in Celsius * 10
            # Handle negative signed int16 correctly
            if temp > 32767:
                temp -= 65536
            return temp / 10.0
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature based on the active season."""
        if self._support_cooling and not self._support_heating:
            temp = self.coordinator.data.get(REG_SUMMER_SETPOINT)
        elif self._support_heating and not self._support_cooling:
            temp = self.coordinator.data.get(REG_WINTER_SETPOINT)
        else:
            season = self.coordinator.data.get(REG_SEASON_IN_USE)
            if season == 0:  # Summer Setpoint
                temp = self.coordinator.data.get(REG_SUMMER_SETPOINT)
            else:            # Winter Setpoint
                temp = self.coordinator.data.get(REG_WINTER_SETPOINT)

        if temp is not None:
            if temp > 32767:
                temp -= 65536
            return temp / 10.0
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        state = self.coordinator.data.get(REG_MACHINE_STATE)
        if state == 0:
            return HVACMode.OFF

        # Device is ON, check specific modes
        fan_only = self.coordinator.data.get(REG_FAN_ONLY_MODE)
        if fan_only == 1:
            return HVACMode.FAN_ONLY

        auto = self.coordinator.data.get(REG_AUTO_MODE)
        if auto == 1 and HVACMode.AUTO in self.hvac_modes:
            return HVACMode.AUTO

        season = self.coordinator.data.get(REG_SEASON_IN_USE)
        if season == 0 and self._support_cooling:
            return HVACMode.COOL
        
        if self._support_heating:
            return HVACMode.HEAT

        return HVACMode.FAN_ONLY

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        if self.coordinator.data.get(REG_AUTO_VENT) == 1:
            return "auto"
        if self.coordinator.data.get(REG_FAN_MIN_STATE) == 1:
            return "low"
        if self.coordinator.data.get(REG_FAN_MED_STATE) == 1:
            return "medium"
        if self.coordinator.data.get(REG_FAN_MAX_STATE) == 1:
            return "high"
        return "auto"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        LOGGER.debug("Setting HVAC mode to: %s", hvac_mode)
        if hvac_mode == HVACMode.OFF:
            # Turn OFF
            await self._hub.write_register(self._hub.cmd_on_off, 0)
        else:
            # Ensure turned ON first
            await self._hub.write_register(self._hub.cmd_on_off, 1)

            # Set mode
            if hvac_mode == HVACMode.COOL:
                await self._hub.write_register(self._hub.cmd_mode, 0) # Summer
            elif hvac_mode == HVACMode.HEAT:
                await self._hub.write_register(self._hub.cmd_mode, 1) # Winter
            elif hvac_mode == HVACMode.FAN_ONLY:
                await self._hub.write_register(self._hub.cmd_mode, 2) # Only Ventilation
            elif hvac_mode == HVACMode.AUTO:
                await self._hub.write_register(self._hub.cmd_mode, 3) # Auto

        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        LOGGER.debug("Setting fan mode to: %s", fan_mode)
        if fan_mode == "auto":
            await self._hub.write_register(self._hub.cmd_fan, 0)
        elif fan_mode == "low":
            await self._hub.write_register(self._hub.cmd_fan, 1)
        elif fan_mode == "medium":
            await self._hub.write_register(self._hub.cmd_fan, 2)
        elif fan_mode == "high":
            await self._hub.write_register(self._hub.cmd_fan, 3)

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature based on configured capabilities and active season."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        target_val = int(round(temperature * 10))

        if self._support_cooling and not self._support_heating:
            LOGGER.debug("Setting Summer setpoint to %s (°C * 10: %s)", temperature, target_val)
            await self._hub.write_register(REG_SUMMER_SETPOINT, target_val)
        elif self._support_heating and not self._support_cooling:
            LOGGER.debug("Setting Winter setpoint to %s (°C * 10: %s)", temperature, target_val)
            await self._hub.write_register(REG_WINTER_SETPOINT, target_val)
        else:
            season = self.coordinator.data.get(REG_SEASON_IN_USE)
            if season == 0:
                LOGGER.debug("Setting Summer setpoint to %s (°C * 10: %s)", temperature, target_val)
                await self._hub.write_register(REG_SUMMER_SETPOINT, target_val)
            else:
                LOGGER.debug("Setting Winter setpoint to %s (°C * 10: %s)", temperature, target_val)
                await self._hub.write_register(REG_WINTER_SETPOINT, target_val)

        await self.coordinator.async_request_refresh()


