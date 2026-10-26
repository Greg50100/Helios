"""DataUpdateCoordinator for the Helios integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS, DOMAIN
from .solar_engine import MeeusSolarEngine, SolarData

_LOGGER = logging.getLogger(__name__)


class HeliosDataUpdateCoordinator(DataUpdateCoordinator[SolarData]):
    """Class to manage recalculating Jean Meeus solar data periodically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        latitude = entry.data.get(CONF_LATITUDE, hass.config.latitude)
        longitude = entry.data.get(CONF_LONGITUDE, hass.config.longitude)
        elevation = entry.data.get(CONF_ELEVATION, hass.config.elevation)
        interval_sec = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS),
        )

        self.engine = MeeusSolarEngine(
            latitude=latitude,
            longitude=longitude,
            elevation_meters=elevation,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval_sec),
        )

    async def _async_update_data(self) -> SolarData:
        """Calculate solar coordinates for the current UTC time."""
        now_utc = dt_util.utcnow()
        return self.engine.calculate(
            now_utc, local_date=dt_util.as_local(now_utc).date()
        )