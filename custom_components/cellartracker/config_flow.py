"""Config flow for CellarTracker."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CellarTrackerApi, CellarTrackerAuthError, CellarTrackerError
from .const import (
    CONF_DOWNLOAD_LABELS,
    CONF_SCAN_INTERVAL,
    DEFAULT_DOWNLOAD_LABELS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

USER_SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class CellarTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Log in with your CellarTracker account."""

    VERSION = 1

    async def _check(self, data: Mapping[str, Any]) -> str | None:
        api = CellarTrackerApi(async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD])
        try:
            await api.validate()
        except CellarTrackerAuthError:
            return "invalid_auth"
        except CellarTrackerError:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            if error := await self._check(user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Create the entry from YAML (cellartracker: username/password)."""
        await self.async_set_unique_id(import_data[CONF_USERNAME].lower())
        self._abort_if_unique_id_configured()
        if error := await self._check(import_data):
            return self.async_abort(reason=error)
        return self.async_create_entry(
            title=import_data[CONF_USERNAME],
            data={CONF_USERNAME: import_data[CONF_USERNAME], CONF_PASSWORD: import_data[CONF_PASSWORD]},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {CONF_USERNAME: entry.data[CONF_USERNAME], CONF_PASSWORD: user_input[CONF_PASSWORD]}
            if error := await self._check(data):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CellarTrackerOptionsFlow()


class CellarTrackerOptionsFlow(OptionsFlow):
    """Update interval and label downloads."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60)),
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=1440)),
                vol.Required(
                    CONF_DOWNLOAD_LABELS, default=opts.get(CONF_DOWNLOAD_LABELS, DEFAULT_DOWNLOAD_LABELS)
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
