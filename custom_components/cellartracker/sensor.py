"""Sensors for CellarTracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import CellarTrackerCoordinator
from .entity import CellarTrackerEntity


@dataclass(frozen=True, kw_only=True)
class CTSensorDescription(SensorEntityDescription):
    """Describes a CellarTracker sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    unit_fn: Callable[[dict[str, Any]], str | None] | None = None


def _avg(d: dict[str, Any]) -> float | None:
    t = d["totals"]
    return round(t["value"] / t["bottles"], 2) if t["bottles"] else None


SENSORS: tuple[CTSensorDescription, ...] = (
    CTSensorDescription(
        key="bottles",
        translation_key="bottles",
        icon="mdi:bottle-wine",
        native_unit_of_measurement="bottles",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["totals"]["bottles"],
    ),
    CTSensorDescription(
        key="value",
        translation_key="value",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=0,
        value_fn=lambda d: d["totals"]["value"],
        unit_fn=lambda d: d["totals"].get("currency") or "EUR",
    ),
    CTSensorDescription(
        key="average_value",
        translation_key="average_value",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=0,
        value_fn=_avg,
        unit_fn=lambda d: d["totals"].get("currency") or "EUR",
    ),
    CTSensorDescription(
        key="wines",
        translation_key="wines",
        icon="mdi:glass-wine",
        native_unit_of_measurement="wines",
        value_fn=lambda d: len(d["wines"]),
        attrs_fn=lambda d: {"wines": d["wines"]},
    ),
    CTSensorDescription(
        key="consumed",
        translation_key="consumed",
        icon="mdi:glass-cocktail",
        native_unit_of_measurement="bottles",
        value_fn=lambda d: d["consumed_stats"].get("this_year", 0),
        attrs_fn=lambda d: {
            "total": d["consumed_stats"].get("total", 0),
            "per_year": d["consumed_stats"].get("per_year", {}),
            "consumed": d["consumed"],
        },
    ),
    CTSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: dt_util.parse_datetime(d["updated"]),
        attrs_fn=lambda d: {"tables": d["tables"], "last_label_download": d.get("labels") or {}},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CellarTrackerCoordinator = entry.runtime_data
    async_add_entities(CellarTrackerSensor(coordinator, desc) for desc in SENSORS)


class CellarTrackerSensor(CellarTrackerEntity, SensorEntity):
    """One CellarTracker sensor."""

    entity_description: CTSensorDescription
    # big lists stay out of the recorder database
    _unrecorded_attributes = frozenset({"wines", "consumed", "tables", "per_year", "last_label_download"})

    def __init__(self, coordinator: CellarTrackerCoordinator, description: CTSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn:
            return self.entity_description.unit_fn(self.coordinator.data)
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.coordinator.data)
        return None
