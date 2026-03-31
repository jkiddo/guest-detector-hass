"""The Guest Detector integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENERGY_ENTITY,
    CONF_HEATING_FLOOR,
    CONF_MIN_EXCESS,
    CONF_THRESHOLD,
    CONF_WINDOW_SIZE,
    DEFAULT_HEATING_FLOOR,
    DEFAULT_MIN_EXCESS,
    DEFAULT_THRESHOLD,
    DEFAULT_WINDOW_SIZE,
    DOMAIN,
)
from .coordinator import EnergyWindowCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Guest Detector from a config entry."""
    energy_entity = entry.data[CONF_ENERGY_ENTITY]
    window_size = int(entry.data.get(CONF_WINDOW_SIZE, DEFAULT_WINDOW_SIZE))
    threshold = float(entry.data.get(CONF_THRESHOLD, DEFAULT_THRESHOLD))
    min_excess = float(entry.data.get(CONF_MIN_EXCESS, DEFAULT_MIN_EXCESS))
    heating_floor = float(entry.data.get(CONF_HEATING_FLOOR, DEFAULT_HEATING_FLOOR))

    coordinator = EnergyWindowCoordinator(
        hass, energy_entity, window_size, threshold, min_excess, heating_floor
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
