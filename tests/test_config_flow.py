"""Config flow tests."""

import re

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cellartracker.const import DOMAIN, XLQUERY_URL

URL = re.compile(re.escape(XLQUERY_URL) + ".*")


async def test_user_flow_bad_then_good(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, text="<html>You are currently not logged into CellarTracker</html>")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USERNAME: "Eddy", CONF_PASSWORD: "x"})
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, text="iWine\tWine\n1\tTest\n")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USERNAME: "Eddy", CONF_PASSWORD: "ok"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eddy"


async def test_import(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, text="iWine\tWine\n1\tTest\n")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={CONF_USERNAME: "Eddy", CONF_PASSWORD: "ok"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
