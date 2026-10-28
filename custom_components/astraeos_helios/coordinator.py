"""DataUpdateCoordinator for the Helios integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS, DOMAIN
from .solar_engine import SolarData, SolarEngine

_LOGGER = logging.getLogger(__name__)

# Event times match the computed elevation to within milliseconds, so a refresh
# one second later is sure to find the new state
TRANSITION_DELAY = timedelta(seconds=1)


class HeliosDataUpdateCoordinator(DataUpdateCoordinator[SolarData]):
    """Class to manage recalculating solar data periodically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        latitude = entry.data.get(CONF_LATITUDE, hass.config.latitude)
        longitude = entry.data.get(CONF_LONGITUDE, hass.config.longitude)
        elevation = entry.options.get(
            CONF_ELEVATION, entry.data.get(CONF_ELEVATION, hass.config.elevation)
        )
        interval_sec = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS),
        )

        self.engine = SolarEngine(
            latitude=latitude,
            longitude=longitude,
            elevation_meters=elevation,
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval_sec),
        )

        self._transition_job = HassJob(
            self._async_refresh_at_transition,
            f"{DOMAIN} transition",
            cancel_on_shutdown=True,
        )
        self._unsub_transition: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> SolarData:
        """Calculate solar coordinates for the current UTC time.

        Daily events follow the solar day, not the civil date, so a dusk after
        local midnight is still shown until it happens. The update interval only
        paces the position sensors: another refresh follows the next event, so
        binary sensors and the solar day switch on time.
        """
        now = dt_util.utcnow()
        data = self.engine.calculate(now)
        self._schedule_transition(data.next_transition(now))
        return data

    def _schedule_transition(self, transition: datetime | None) -> None:
        """Schedule a refresh right after the next event, replacing the last one."""
        self._cancel_transition()
        if transition is not None:
            self._unsub_transition = async_track_point_in_utc_time(
                self.hass, self._transition_job, transition + TRANSITION_DELAY
            )

    def _cancel_transition(self) -> None:
        """Cancel the refresh scheduled after the next event."""
        if self._unsub_transition is not None:
            self._unsub_transition()
            self._unsub_transition = None

    async def _async_refresh_at_transition(self, _now: datetime) -> None:
        """Refresh once an event has changed a binary state or the solar day."""
        self._unsub_transition = None
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Cancel scheduled refreshes, including the one after the next event."""
        await super().async_shutdown()
        self._cancel_transition()