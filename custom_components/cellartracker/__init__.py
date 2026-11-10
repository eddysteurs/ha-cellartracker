"""CellarTracker integration: your wine cellar in Home Assistant."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import CellarTrackerCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
        )
    },
    extra=vol.ALLOW_EXTRA,
)

type CellarTrackerConfigEntry = ConfigEntry[CellarTrackerCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Optional one-time import from configuration.yaml."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(config[DOMAIN])
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CellarTrackerConfigEntry) -> bool:
    coordinator = CellarTrackerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: CellarTrackerConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CellarTrackerConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
