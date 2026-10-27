"""Constants for the Helios integration."""

from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "astraeos_helios"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)