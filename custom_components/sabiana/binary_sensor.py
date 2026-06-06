"""Support for Sabiana Binary Sensors (Alarms and Faults)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    REG_T1_FAULT,
    REG_T2_FAULT,
    REG_T3_FAULT,
    REG_CONDENS_ALARM,
    REG_T2_PROBE_FOUND,
    REG_DIP3_T3_PROBE_ON,
)

@dataclass(frozen=True, kw_only=True)
class SabianaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Sabiana binary sensor entities."""

    is_on_fn: Callable[[dict], bool | None]

BINARY_SENSORS: tuple[SabianaBinarySensorEntityDescription, ...] = (
    SabianaBinarySensorEntityDescription(
        key="t1_fault",
        name="T1 Sensor Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.get(REG_T1_FAULT) == 1,
    ),
    SabianaBinarySensorEntityDescription(
        key="t2_fault",
        name="T2 Sensor Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.get(REG_T2_FAULT) == 1,
    ),
    SabianaBinarySensorEntityDescription(
        key="t3_fault",
        name="T3 Sensor Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.get(REG_T3_FAULT) == 1,
    ),
    SabianaBinarySensorEntityDescription(
        key="condensation_alarm",
        name="Condensation Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.get(REG_CONDENS_ALARM) == 1,
    ),
    SabianaBinarySensorEntityDescription(
        key="t2_probe_found",
        name="T2 Probe Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda data: data.get(REG_T2_PROBE_FOUND) == 1,
    ),
    SabianaBinarySensorEntityDescription(
        key="t3_probe_enabled",
        name="T3 Probe Enabled",
        is_on_fn=lambda data: data.get(REG_DIP3_T3_PROBE_ON) == 1,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sabiana binary sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        SabianaBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSORS
    ]
    async_add_entities(entities, True)

class SabianaBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Sabiana Binary Sensor."""

    entity_description: SabianaBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        description: SabianaBinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sabiana Fan Coil",
            manufacturer="Sabiana",
            model="Carisma Fly CVP-ECM-MB",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)
