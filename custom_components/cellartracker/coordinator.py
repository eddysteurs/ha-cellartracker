"""Data update coordinator for CellarTracker."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CellarTrackerApi, CellarTrackerAuthError, CellarTrackerError
from .const import (
    CONF_DOWNLOAD_LABELS,
    CONF_SCAN_INTERVAL,
    CONSUMED_LIMIT,
    DEFAULT_DOWNLOAD_LABELS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TABLE_CONSUMED,
    TABLE_INVENTORY,
)
from .images import ImageManager
from .parse import build_consumed, build_inventory

_LOGGER = logging.getLogger(__name__)


class CellarTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch inventory and consumed bottles once per interval."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL)
        interval = timedelta(minutes=int(minutes)) if minutes else DEFAULT_SCAN_INTERVAL
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=interval)
        session = async_get_clientsession(hass)
        self.api = CellarTrackerApi(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        self.images = ImageManager(hass, session, entry.entry_id)

    async def _async_update_data(self) -> dict[str, Any]:
        tables: dict[str, dict[str, Any]] = {}
        try:
            inv_rows = await self.api.fetch_table(TABLE_INVENTORY)
        except CellarTrackerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CellarTrackerError as err:
            raise UpdateFailed(str(err)) from err
        tables[TABLE_INVENTORY] = {"rows": len(inv_rows), "columns": list(inv_rows[0].keys()) if inv_rows else []}

        consumed_ok = True
        consumed_rows: list[dict[str, str]] = []
        try:
            consumed_rows = await self.api.fetch_table(TABLE_CONSUMED)
            tables[TABLE_CONSUMED] = {
                "rows": len(consumed_rows),
                "columns": list(consumed_rows[0].keys()) if consumed_rows else [],
            }
        except CellarTrackerError as err:
            consumed_ok = False
            _LOGGER.warning("CellarTracker consumed list not available: %s", err)
            tables[TABLE_CONSUMED] = {"error": str(err)}

        wines, totals = build_inventory(inv_rows)
        if consumed_ok or not self.data:
            producers = {w["iWine"]: w["producer"] for w in wines if w.get("iWine") and w.get("producer")}
            consumed, consumed_stats = build_consumed(consumed_rows, CONSUMED_LIMIT, producers)
        else:  # keep the previous list when only the consumed table failed
            consumed = self.data.get("consumed", [])
            consumed_stats = self.data.get("consumed_stats", {})

        if self.config_entry.options.get(CONF_DOWNLOAD_LABELS, DEFAULT_DOWNLOAD_LABELS):
            wanted = [w["iWine"] for w in wines] + [c["iWine"] for c in consumed]
            await self.images.async_download_missing([w for w in wanted if w])
        await self.images.async_resolve(wines)
        await self.images.async_resolve(consumed)

        return {
            "wines": wines,
            "totals": totals,
            "consumed": consumed,
            "consumed_stats": consumed_stats,
            "tables": tables,
            "labels": self.images.last_result,
            "updated": dt_util.utcnow().isoformat(),
        }
