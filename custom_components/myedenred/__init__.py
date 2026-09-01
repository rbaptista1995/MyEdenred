"""The my_edenred integration."""
from __future__ import annotations
import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.myedenred import MY_EDENRED, MyEdenredAuthError, MyEdenredError
from .coordinator import MyEdenredDataUpdateCoordinator
from .const import DOMAIN

__version__ = json.loads(Path(__file__).with_name("manifest.json").read_text(encoding="utf-8"))["version"]
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the component from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = async_get_clientsession(hass, True)
    config = entry.data
    api = MY_EDENRED(session, config.get("cookies"))
    token = config.get("token")

    if not token:
        raise ConfigEntryAuthFailed("MyEdenred session is missing")

    try:
        cards = await api.getCards(token)
    except MyEdenredAuthError as err:
        # A restart must only use the saved session. Logging in here would send
        # a fresh 2FA email every time Home Assistant loads the integration.
        raise ConfigEntryAuthFailed("MyEdenred session expired") from err
    except MyEdenredError as err:
        raise ConfigEntryNotReady("Could not retrieve MyEdenred cards") from err

    accounts = {}
    for card in cards:
        try:
            accounts[card.id] = await api.getAccountDetails(card.id, token)
        except MyEdenredAuthError as err:
            raise ConfigEntryAuthFailed("MyEdenred token expired") from err
        except MyEdenredError as err:
            raise ConfigEntryNotReady(
                f"Could not retrieve MyEdenred account data for card {card.id}"
            ) from err

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, "token": token, "cookies": dict(api.cookies)},
    )
    coordinator = MyEdenredDataUpdateCoordinator(hass, entry, api, cards, accounts)
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "cards": cards,
    }

    # Update compatibility with Home Assistant 2022.12
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return result

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
