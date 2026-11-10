"""Bottle images: your own photos in /config/www/wine plus downloaded labels."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    BASE_URL,
    DOMAIN,
    IMAGE_DIR,
    IMAGE_EXTENSIONS,
    LABEL_PREFIX,
    LABEL_RETRY_DAYS,
    LABELS_PER_UPDATE,
    WINE_URL,
)

_LOGGER = logging.getLogger(__name__)

OG_IMAGE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
LABEL_IMG = re.compile(r'(?:src|href)=["\']([^"\']*label[^"\']*\.(?:jpe?g|png|webp))["\']', re.I)
BAD_HINTS = ("logo", "nolabel", "no_label", "default", "placeholder", "spacer")


class ImageManager:
    """Find local images and fetch missing labels from CellarTracker."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, entry_id: str) -> None:
        self.hass = hass
        self._session = session
        self._dir = hass.config.path("www", IMAGE_DIR)
        self._store: Store[dict[str, float]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.labels_v2")
        self._failed: dict[str, float] | None = None
        self.last_result: dict[str, Any] = {}

    def _scan(self) -> dict[str, tuple[str, int]]:
        """Map lower-case file stem -> (file name, mtime)."""
        os.makedirs(self._dir, exist_ok=True)
        found: dict[str, tuple[str, int]] = {}
        for name in os.listdir(self._dir):
            stem, ext = os.path.splitext(name)
            if ext.lower() in IMAGE_EXTENSIONS:
                try:
                    mtime = int(os.path.getmtime(os.path.join(self._dir, name)))
                except OSError:
                    mtime = 0
                found[stem.lower()] = (name, mtime)
        return found

    async def async_resolve(self, records: list[dict[str, Any]]) -> None:
        """Set 'image' (URL or None) and 'image_source' on each record."""
        files = await self.hass.async_add_executor_job(self._scan)
        for rec in records:
            iwine = str(rec.get("iWine") or "")
            own = files.get(iwine.lower())
            label = files.get(f"{LABEL_PREFIX}{iwine}".lower())
            if own:
                rec["image"] = f"/local/{IMAGE_DIR}/{own[0]}?v={own[1]}"
                rec["image_source"] = "own"
            elif label:
                rec["image"] = f"/local/{IMAGE_DIR}/{label[0]}?v={label[1]}"
                rec["image_source"] = "cellartracker"
            else:
                rec["image"] = None
                rec["image_source"] = None

    async def async_download_missing(self, iwines: list[str]) -> int:
        """Try to fetch labels for wines without any image. Returns number downloaded."""
        if self._failed is None:
            self._failed = await self._store.async_load() or {}
        files = await self.hass.async_add_executor_job(self._scan)
        now = time.time()
        todo = []
        for iwine in dict.fromkeys(iwines):  # keep order, drop duplicates
            if not iwine:
                continue
            if iwine.lower() in files or f"{LABEL_PREFIX}{iwine}".lower() in files:
                continue
            if now - self._failed.get(iwine, 0) < LABEL_RETRY_DAYS * 86400:
                continue
            todo.append(iwine)
            if len(todo) >= LABELS_PER_UPDATE:
                break

        done = 0
        for iwine in todo:
            try:
                ok, why = await self._download_one(iwine)
            except Exception as err:  # noqa: BLE001 - never break the update for an image
                ok, why = False, f"error: {err}"
            self.last_result = {"iWine": iwine, "ok": ok, "detail": why, "at": time.strftime("%Y-%m-%d %H:%M")}
            _LOGGER.debug("Label for %s: %s", iwine, why)
            if ok:
                done += 1
                self._failed.pop(iwine, None)
            else:
                self._failed[iwine] = now
            await asyncio.sleep(2)
        if todo:
            await self._store.async_save(self._failed)
            _LOGGER.info("CellarTracker labels: %s of %s downloaded", done, len(todo))
        return done

    async def _download_one(self, iwine: str) -> tuple[bool, str]:
        timeout = aiohttp.ClientTimeout(total=30)
        async with self._session.get(WINE_URL, params={"iWine": iwine}, timeout=timeout) as resp:
            if resp.status != 200:
                return False, f"wine page HTTP {resp.status} ({resp.url.host})"
            html = await resp.text(errors="replace")
        candidates = OG_IMAGE.findall(html) + LABEL_IMG.findall(html)
        url = next(
            (c for c in candidates if not any(h in c.lower() for h in BAD_HINTS)),
            None,
        )
        if not url:
            hint = html[html.lower().find("label") - 80 : html.lower().find("label") + 120] if "label" in html.lower() else html[:160]
            return False, f"no label image on page ({len(html)} chars): {' '.join(hint.split())[:200]}"
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = BASE_URL + url
        async with self._session.get(url, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if resp.status != 200 or not ctype.startswith("image/"):
                return False, f"image HTTP {resp.status} {ctype} {url}"
            data = await resp.read()
        if len(data) < 2000:  # tiny = icon / placeholder
            return False, f"image too small ({len(data)} bytes) {url}"
        ext = ".png" if "png" in ctype else ".webp" if "webp" in ctype else ".jpg"
        path = os.path.join(self._dir, f"{LABEL_PREFIX}{iwine}{ext}")

        def _write() -> None:
            with open(path, "wb") as fh:
                fh.write(data)

        await self.hass.async_add_executor_job(_write)
        return True, f"saved {os.path.basename(path)} from {url}"
