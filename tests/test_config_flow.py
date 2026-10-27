"""Tests for the Helios config and options flows."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip(
    "pytest_homeassistant_custom_component",
    reason="requires pytest-homeassistant-custom-component (see requirements_test.txt)",
)

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.helios.const import CONF_UPDATE_INTERVAL, DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

USER_INPUT = {
    CONF_NAME: "Home",
    CONF_LATITUDE: 48.8566,
    CONF_LONGITUDE: 2.3522,
    CONF_ELEVATION: 35.0,
    CONF_UPDATE_INTERVAL: 60,
}
UNIQUE_ID = "48.8566_2.3522"


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("custom_components.helios.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == UNIQUE_ID


async def test_user_flow_aborts_on_configured_location(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=UNIQUE_ID, data=USER_INPUT).add_to_hass(
        hass
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=UNIQUE_ID, data=USER_INPUT)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # The form starts from the values entered during setup
    defaults = {str(key): key.default() for key in result["data_schema"].schema}
    assert defaults == {CONF_ELEVATION: 35.0, CONF_UPDATE_INTERVAL: 60}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ELEVATION: 1000, CONF_UPDATE_INTERVAL: 120}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_ELEVATION: 1000.0, CONF_UPDATE_INTERVAL: 120}
