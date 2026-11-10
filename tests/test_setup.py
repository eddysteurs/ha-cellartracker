"""Basic setup test with mocked CellarTracker responses."""

import re

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cellartracker.const import DOMAIN, XLQUERY_URL, WINE_URL

INVENTORY = (
    "iInventory\tPrice\tValuation\tCurrency\tLocation\tBin\tiWine\tType\tColor\tCategory\tVintage\tWine\tProducer\tVarietal\tCountry\tBeginConsume\tEndConsume\n"
    "1\t20\t24\tEUR\twijnkast\t3\t5534061\tWhite\tWhite\tDry\t2025\tCloudy Bay Sauvignon Blanc\tCloudy Bay\tSauvignon Blanc\tNew Zealand\t2025\t2027\n"
    "2\t20\t24\tEUR\tdoos35\t\t5534061\tWhite\tWhite\tDry\t2025\tCloudy Bay Sauvignon Blanc\tCloudy Bay\tSauvignon Blanc\tNew Zealand\t2025\t2027\n"
    "3\t30\t26\tEUR\twijnkast\t1\t304936\tWhite - Sparkling\tWhite\tSparkling\t1001\tBaron Albert Brut\tBaron Albert\tChampagne Blend\tFrance\t2013\t2020\n"
)
CONSUMED = (
    "iConsumed\tiWine\tType\tConsumed\tShortType\tValue\tWine\tVintage\tProducer\tColor\n"
    "1\t5534061\tDrank\t10/3/2026\tDrank\t24\tCloudy Bay SB\t2024\tCloudy Bay\tWhite\n"
)


async def test_setup(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    aioclient_mock.get(XLQUERY_URL, params={"User": "u", "Password": "p", "Table": "Inventory", "Format": "tab", "Location": "1"}, text=INVENTORY)
    aioclient_mock.get(XLQUERY_URL, params={"User": "u", "Password": "p", "Table": "Consumed", "Format": "tab", "Location": "1"}, text=CONSUMED)
    aioclient_mock.get(re.compile(re.escape(WINE_URL) + ".*"), text="<html>no image</html>")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_USERNAME: "u", CONF_PASSWORD: "p"}, unique_id="u")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    states = {s.entity_id: s for s in hass.states.async_all()}
    for eid, s in sorted(states.items()):
        print(eid, s.state, s.attributes.get("unit_of_measurement"))
    wines = hass.states.get("sensor.cellartracker_wines")
    assert wines.state == "2"
    assert hass.states.get("sensor.cellartracker_bottles").state == "3"
    w = wines.attributes["wines"]
    print(w)
    assert w[0]["vintage"] == "NV"
    c = hass.states.get("sensor.cellartracker_consumed_this_year")
    print(c.state, c.attributes["consumed"])
    assert hass.states.get("button.cellartracker_refresh") is not None


async def test_bad_login(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    aioclient_mock.get(re.compile(re.escape(XLQUERY_URL) + ".*"), text="<html>You are currently not logged into CellarTracker</html>")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_USERNAME: "u", CONF_PASSWORD: "bad"}, unique_id="u")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state.name == "SETUP_ERROR"
