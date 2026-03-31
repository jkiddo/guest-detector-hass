"""Config flow for Guest Detector integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENERGY_ENTITY,
    CONF_HEATING_FLOOR,
    CONF_MIN_EXCESS,
    CONF_THRESHOLD,
    CONF_WINDOW_SIZE,
    DEFAULT_ENERGY_ENTITY,
    DEFAULT_HEATING_FLOOR,
    DEFAULT_MIN_EXCESS,
    DEFAULT_THRESHOLD,
    DEFAULT_WINDOW_SIZE,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_ENERGY_ENTITY, default=DEFAULT_ENERGY_ENTITY
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor"),
        ),
        vol.Required(
            CONF_WINDOW_SIZE, default=DEFAULT_WINDOW_SIZE
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=7, max=90, step=1, mode=selector.NumberSelectorMode.BOX
            ),
        ),
        vol.Required(
            CONF_THRESHOLD, default=DEFAULT_THRESHOLD
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1.1, max=5.0, step=0.1, mode=selector.NumberSelectorMode.BOX
            ),
        ),
        vol.Required(
            CONF_MIN_EXCESS, default=DEFAULT_MIN_EXCESS
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.5, max=20.0, step=0.5, mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="kWh",
            ),
        ),
        vol.Required(
            CONF_HEATING_FLOOR, default=DEFAULT_HEATING_FLOOR
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=20.0, step=0.5, mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="kWh",
            ),
        ),
    }
)


class GuestDetectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guest Detector."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ENERGY_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Guest Detector", data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA
        )
