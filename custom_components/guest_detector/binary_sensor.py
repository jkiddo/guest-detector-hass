"""Binary sensor for Guest Detector - indicates if guest presence is detected."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyWindowCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Guest Detector binary sensor from a config entry."""
    coordinator: EnergyWindowCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GuestDetectedBinarySensor(coordinator, entry)])


class GuestDetectedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is ON when energy usage suggests guest presence."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_name = "Guest Detected"

    def __init__(self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_guest_detected"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("is_guest")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {
            "baseline_kwh": data.get("baseline"),
            "current_kwh": data.get("current"),
            "excess_kwh": data.get("excess"),
            "ratio": data.get("ratio"),
            "threshold": data.get("threshold"),
            "min_excess_kwh": data.get("min_excess"),
            "window_size_days": data.get("window_size"),
            "std_dev_kwh": data.get("std_dev"),
            "heating_season": data.get("heating_season"),
            "heating_floor_kwh": data.get("heating_floor"),
        }
