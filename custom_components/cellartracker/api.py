"""Small client for CellarTracker's export (xlquery.asp) interface."""

from __future__ import annotations

import csv
import io
import logging

import aiohttp

from .const import XLQUERY_URL

_LOGGER = logging.getLogger(__name__)

NOT_LOGGED_IN_MARKERS = ("not logged into cellartracker", "<html")


class CellarTrackerError(Exception):
    """Generic error talking to CellarTracker."""


class CellarTrackerAuthError(CellarTrackerError):
    """Wrong user name or password."""


class CellarTrackerApi:
    """Fetch tables from CellarTracker as lists of dicts."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def fetch_table(self, table: str) -> list[dict[str, str]]:
        """Fetch one export table (Format=tab) and parse it."""
        params = {
            "User": self._username,
            "Password": self._password,
            "Table": table,
            "Format": "tab",
            "Location": "1",
        }
        try:
            async with self._session.get(
                XLQUERY_URL, params=params, timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status != 200:
                    raise CellarTrackerError(f"{table}: HTTP {resp.status}")
                raw = await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CellarTrackerError(f"{table}: {err}") from err

        # CellarTracker exports in Windows-1252, fall back to UTF-8 when it is valid UTF-8
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")

        head = text[:500].lower()
        if any(marker in head for marker in NOT_LOGGED_IN_MARKERS):
            raise CellarTrackerAuthError("CellarTracker refused the login")

        text = text.lstrip("﻿")
        if not text.strip():
            return []
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        rows = []
        for row in reader:
            rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items() if k})
        return rows

    async def validate(self) -> None:
        """Raise when the login does not work."""
        await self.fetch_table("Inventory")
