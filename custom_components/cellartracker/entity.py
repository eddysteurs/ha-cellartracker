"""Base entity for CellarTracker."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import CellarTrackerCoordinator


class CellarTrackerEntity(CoordinatorEntity[CellarTrackerCoordinator]):
    """Common device info and naming."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CellarTrackerCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="CellarTracker",
            manufacturer="CellarTracker",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=BASE_URL,
        )
