"""Config flow for Helios integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS, DOMAIN


class HeliosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Helios."""

    VERSION = 1

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
                ): vol.Coerce(float),
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL_SECONDS
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)