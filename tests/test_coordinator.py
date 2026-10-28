"""Tests for refreshing Helios right after the events that change a state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip(
    "pytest_homeassistant_custom_component",
    reason="requires pytest-homeassistant-custom-component (see requirements_test.txt)",
)

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.astraeos_helios.const import CONF_UPDATE_INTERVAL, DOMAIN
from custom_components.astraeos_helios.solar_engine import SolarEngine

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

LATITUDE, LONGITUDE, ELEVATION = 48.8566, 2.3522, 35.0
ABOVE_HORIZON = "binary_sensor.home_sun_above_horizon"
GOLDEN_HOUR = "binary_sensor.home_golden_hour"
BLUE_HOUR = "binary_sensor.home_blue_hour"
SUNRISE = "sensor.home_sunrise"


async def test_states_switch_at_events_between_hourly_refreshes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Paris, 2024-06-21 evening, refreshed hourly: every state switches on time."""
    day = SolarEngine(LATITUDE, LONGITUDE, ELEVATION).calculate(
        datetime(2024, 6, 21, 12, tzinfo=timezone.utc)
    )
    freezer.move_to(day.golden_hour_dusk - timedelta(minutes=5))
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id=f"{LATITUDE}_{LONGITUDE}",
        data={
            CONF_NAME: "Home",
            CONF_LATITUDE: LATITUDE,
            CONF_LONGITUDE: LONGITUDE,
            CONF_ELEVATION: ELEVATION,
            CONF_UPDATE_INTERVAL: 3600,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    async def move_to(moment: datetime) -> None:
        freezer.move_to(moment)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    def states() -> tuple[str, str, str]:
        return tuple(
            hass.states.get(entity_id).state
            for entity_id in (ABOVE_HORIZON, GOLDEN_HOUR, BLUE_HOUR)
        )

    # Each step is 2 s past an event and well within the hourly refresh
    assert states() == ("on", "off", "off")
    await move_to(day.golden_hour_dusk + timedelta(seconds=2))
    assert states() == ("on", "on", "off")
    await move_to(day.sunset + timedelta(seconds=2))
    assert states() == ("off", "on", "off")
    await move_to(day.blue_hour_dusk + timedelta(seconds=2))
    assert states() == ("off", "off", "on")
    await move_to(day.civil_dusk + timedelta(seconds=2))
    assert states() == ("off", "off", "off")

    # The timestamps move on to the next solar day at solar midnight
    await move_to(day.solar_midnight - timedelta(minutes=1))
    assert dt_util.parse_datetime(hass.states.get(SUNRISE).state) < day.solar_noon
    await move_to(day.solar_midnight + timedelta(seconds=2))
    assert dt_util.parse_datetime(hass.states.get(SUNRISE).state) > day.solar_midnight

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
