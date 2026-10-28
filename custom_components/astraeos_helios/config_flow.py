"""Config flow for Helios integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS, DOMAIN

UPDATE_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
# From below the lowest shore (Dead Sea, -430 m) to above the highest summit (8849 m)
ELEVATION_VALIDATOR = vol.All(vol.Coerce(float), vol.Range(min=-500, max=9000))


class HeliosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Helios."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HeliosOptionsFlow:
        """Return the options flow handler."""
        return HeliosOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_LATITUDE]}_{user_input[CONF_LONGITUDE]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Helios"): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
                vol.Required(
                    CONF_ELEVATION, default=self.hass.config.elevation
                ): ELEVATION_VALIDATOR,
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL_SECONDS
                ): UPDATE_INTERVAL_VALIDATOR,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)


class HeliosOptionsFlow(config_entries.OptionsFlow):
    """Handle Helios options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the elevation and update interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Options override the values entered during the initial setup
        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ELEVATION,
                    default=current.get(CONF_ELEVATION, self.hass.config.elevation),
                ): ELEVATION_VALIDATOR,
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS
                    ),
                ): UPDATE_INTERVAL_VALIDATOR,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)