"""Binary sensor platform for Helios integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
from .solar_engine import SolarData


@dataclass(frozen=True, kw_only=True)
class HeliosBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Helios binary sensor entity."""

    is_on_fn: Callable[[SolarData], bool]


BINARY_SENSOR_TYPES: tuple[HeliosBinarySensorEntityDescription, ...] = (
    HeliosBinarySensorEntityDescription(
        key="above_horizon",
        translation_key="above_horizon",
        icon="mdi:white-balance-sunny",
        is_on_fn=lambda data: data.is_above_horizon,
    ),
    HeliosBinarySensorEntityDescription(
        key="golden_hour",
        translation_key="golden_hour",
        icon="mdi:weather-sunset",
        is_on_fn=lambda data: data.is_golden_hour,
    ),
    HeliosBinarySensorEntityDescription(
        key="blue_hour",
        translation_key="blue_hour",
        icon="mdi:weather-night",
        is_on_fn=lambda data: data.is_blue_hour,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Helios binary sensors based on a config entry."""
    coordinator: HeliosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HeliosBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_TYPES
    )


class HeliosBinarySensor(
    CoordinatorEntity[HeliosDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Helios binary sensor."""

    entity_description: HeliosBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeliosDataUpdateCoordinator,
        description: HeliosBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="astraeos",
            model="Solar calculator",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)