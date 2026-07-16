"""The my_edenred integration."""
from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api.myedenred import (
    MY_EDENRED,
    MyEdenredAuthError,
    MyEdenredChallengeRequired,
    MyEdenredError,
)
from .const import DOMAIN

__version__ = "2.2.0"
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

PLATFORMS: list[str] = ["sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType):
    # Return boolean to indicate that initialization was successful.
    _LOGGER.debug("async_setup")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the component from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = async_get_clientsession(hass, True)
    config = entry.data
    api = MY_EDENRED(session, config.get("cookies"))
    token = config.get("token")

    if not token:
        try:
            result = await api.authenticate(config["username"], config["password"])
            token = result["token"]
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **config,
                    "token": token,
                    "cookies": result.get("cookies", {}),
                },
            )
        except MyEdenredChallengeRequired as err:
            raise ConfigEntryAuthFailed("MyEdenred requires email 2FA") from err
        except MyEdenredError as err:
            raise ConfigEntryNotReady("Could not authenticate with MyEdenred") from err

    try:
        cards = await api.getCards(token)
    except MyEdenredAuthError as err:
        raise ConfigEntryAuthFailed("MyEdenred token expired") from err
    except MyEdenredError as err:
        raise ConfigEntryNotReady("Could not retrieve MyEdenred cards") from err

    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            "token": token,
            "cookies": api.cookies,
        },
    )
    hass.data[DOMAIN][entry.entry_id] = {"api": api, "cards": cards}
    
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
