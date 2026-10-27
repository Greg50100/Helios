"""Tests for setting up, reloading and unloading Helios."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip(
    "pytest_homeassistant_custom_component",
    reason="requires pytest-homeassistant-custom-component (see requirements_test.txt)",
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.helios.const import CONF_UPDATE_INTERVAL, DOMAIN
from custom_components.helios.sensor import SENSOR_TYPES

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="48.8566_2.3522",
        data={
            CONF_NAME: "Home",
            CONF_LATITUDE: 48.8566,
            CONF_LONGITUDE: 2.3522,
            CONF_ELEVATION: 35.0,
            CONF_UPDATE_INTERVAL: 60,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_and_unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == len(SENSOR_TYPES) + 1
    for entity in entities:
        assert hass.states.get(entity.entity_id) is not None, entity.entity_id

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_options_update_reloads_entry(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(
        entry, options={CONF_ELEVATION: 1000.0, CONF_UPDATE_INTERVAL: 120}
    )
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.engine.elevation_meters == 1000.0
    assert coordinator.update_interval == timedelta(seconds=120)
