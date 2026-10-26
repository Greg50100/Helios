"""Binary sensor platform for Helios integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HeliosDataUpdateCoordinator

BINARY_SENSOR_DESCRIPTION = BinarySensorEntityDescription(
    key="above_horizon",
    translation_key="above_horizon",
    icon="mdi:white-balance-sunny",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Helios binary sensor."""
    coordinator: HeliosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HeliosAboveHorizonBinarySensor(coordinator)])


class HeliosAboveHorizonBinarySensor(
    CoordinatorEntity[HeliosDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor indicating if the sun is above the horizon."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HeliosDataUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = BINARY_SENSOR_DESCRIPTION
        self._attr_unique_id = f"{coordinator.entry.entry_id}_above_horizon"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Jean Meeus Algorithms",
            model="Astronomical Algorithms (2nd Ed.)",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return True if the sun is above the horizon."""
        return self.coordinator.data.is_above_horizon