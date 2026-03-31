"""Sliding window energy analysis sensors for Guest Detector."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
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
    """Set up Guest Detector sensors from a config entry."""
    coordinator: EnergyWindowCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            SlidingWindowBaselineSensor(coordinator, entry),
            SlidingWindowCurrentSensor(coordinator, entry),
            SlidingWindowRatioSensor(coordinator, entry),
            SlidingWindowStdDevSensor(coordinator, entry),
        ]
    )


class SlidingWindowBaselineSensor(CoordinatorEntity, SensorEntity):
    """Sliding window baseline average energy (kWh)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_baseline"
        self._attr_name = "Energy Baseline"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("baseline")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {
            "method": "25th percentile",
            "window_size_days": data.get("window_size"),
            "days_available": data.get("days_available"),
            "window_start": data.get("window_start"),
            "window_end": data.get("window_end"),
            "heating_season": data.get("heating_season"),
            "heating_floor_kwh": data.get("heating_floor"),
        }


class SlidingWindowCurrentSensor(CoordinatorEntity, SensorEntity):
    """Most recent day's energy consumption (kWh)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current"
        self._attr_name = "Energy Current Day"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("current")


class SlidingWindowRatioSensor(CoordinatorEntity, SensorEntity):
    """Ratio of current energy to sliding window baseline."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ratio"
        self._attr_name = "Energy Ratio"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("ratio")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {
            "threshold": data.get("threshold"),
            "min_excess_kwh": data.get("min_excess"),
        }


class SlidingWindowStdDevSensor(CoordinatorEntity, SensorEntity):
    """Standard deviation of energy in the sliding window."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EnergyWindowCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_std_dev"
        self._attr_name = "Energy Std Dev"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("std_dev")
