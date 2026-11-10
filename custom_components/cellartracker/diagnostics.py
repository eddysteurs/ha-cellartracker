"""Diagnostics for CellarTracker (password removed)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = entry.runtime_data.data or {}
    return {
        "entry": async_redact_data(dict(entry.data), {CONF_PASSWORD, CONF_USERNAME}),
        "options": dict(entry.options),
        "tables": data.get("tables"),
        "totals": data.get("totals"),
        "consumed_stats": data.get("consumed_stats"),
        "sample_wine": (data.get("wines") or [None])[0],
        "sample_consumed": (data.get("consumed") or [None])[0],
    }
