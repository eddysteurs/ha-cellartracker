"""Refresh button for CellarTracker."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CellarTrackerCoordinator
from .entity import CellarTrackerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([CellarTrackerRefreshButton(entry.runtime_data)])


class CellarTrackerRefreshButton(CellarTrackerEntity, ButtonEntity):
    """Fetch new data now (also picks up new photos in www/wine)."""

    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: CellarTrackerCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
