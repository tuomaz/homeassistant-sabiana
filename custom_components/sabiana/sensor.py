"""Support for Sabiana Sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    REG_T1,
    REG_T2,
    REG_T3,
    REG_SLAVE_MASTER,
    REG_BOARD_TIME,
    REG_MACHINE_TIME,
    REG_TMB_PRESENT,
    REG_IR_PRESENT,
    REG_DIP3_T3_PROBE_ON,
    REG_T2_PROBE_FOUND,
)

@dataclass(frozen=True, kw_only=True)
class SabianaSensorEntityDescription(SensorEntityDescription):
    """Class describing Sabiana sensor entities."""

    value_fn: Callable[[dict, Any], float | int | str | None]

def get_temp_value(data: dict, register: int, presence_register: int | None = None) -> float | None:
    """Helper to convert registered Celsius * 10 to float, respecting probe presence."""
    if presence_register is not None and data.get(presence_register) != 1:
        return None
    val = data.get(register)
    if val is None:
        return None
    if val > 32767:
        val -= 65536
    return val / 10.0

SENSORS: tuple[SabianaSensorEntityDescription, ...] = (
    SabianaSensorEntityDescription(
        key="t1_temperature",
        name="Ambient Air Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, hub: get_temp_value(data, REG_T1),
    ),
    SabianaSensorEntityDescription(
        key="t2_temperature",
        name="Coil Water Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, hub: get_temp_value(data, REG_T2, REG_T2_PROBE_FOUND),
    ),
    SabianaSensorEntityDescription(
        key="t3_temperature",
        name="Minimum Probe Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, hub: get_temp_value(data, REG_T3, REG_DIP3_T3_PROBE_ON),
    ),
    SabianaSensorEntityDescription(
        key="board_power_on_time",
        name="Board Power-On Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data, hub: round(data.get(hub.reg_board_time, 0) / 3600, 1),
    ),
    SabianaSensorEntityDescription(
        key="machine_on_time",
        name="Machine On Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data, hub: round(data.get(hub.reg_machine_time, 0) / 3600, 1),
    ),
    SabianaSensorEntityDescription(
        key="tmb_present",
        name="T-MB Controller Present",
        value_fn=lambda data, hub: "Yes" if data.get(hub.reg_tmb_present) == 1 else "No",
    ),
    SabianaSensorEntityDescription(
        key="ir_present",
        name="IR Receiver Present",
        value_fn=lambda data, hub: "Yes" if data.get(hub.reg_ir_present) == 1 else "No",
    ),
    SabianaSensorEntityDescription(
        key="slave_master",
        name="Slave/Master Mode",
        value_fn=lambda data, hub: "Slave" if data.get(REG_SLAVE_MASTER) == 1 else ("Master" if data.get(REG_SLAVE_MASTER) == 2 else None),
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sabiana sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    hub = data["hub"]

    entities = [
        SabianaSensor(coordinator, description, entry, hub)
        for description in SENSORS
    ]
    async_add_entities(entities, True)

class SabianaSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sabiana Sensor."""

    entity_description: SabianaSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        description: SabianaSensorEntityDescription,
        entry: ConfigEntry,
        hub: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._hub = hub
        
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sabiana Fan Coil",
            manufacturer="Sabiana",
            model="Carisma Fly CVP-ECM-MB",
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data, self._hub)

