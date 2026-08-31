"""Coordinate MyEdenred data updates for a config entry."""
from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.account import Account
from .api.card import Card
from .api.myedenred import MY_EDENRED, MyEdenredAuthError, MyEdenredError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=10)


class MyEdenredDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Account]]):
    """Fetch every card once per interval using the persisted session."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: MY_EDENRED,
        cards: list[Card],
        accounts: dict[str, Account],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.api = api
        self.cards = cards
        self.async_set_updated_data(accounts)

    async def _async_update_data(self) -> dict[str, Account]:
        """Refresh card accounts without ever triggering a new login."""
        token = self.entry.data.get("token")
        if not token:
            raise ConfigEntryAuthFailed("MyEdenred session is missing")

        try:
            accounts = {
                card.id: await self.api.getAccountDetails(card.id, token)
                for card in self.cards
            }
        except MyEdenredAuthError as err:
            # Edenred requires a user-initiated login (and potentially email 2FA).
            # Do not call authenticate here: it would send a code on every poll.
            raise ConfigEntryAuthFailed("MyEdenred session expired") from err
        except (aiohttp.ClientError, MyEdenredError) as err:
            raise UpdateFailed(f"Could not update MyEdenred data: {err}") from err

        cookies = dict(self.api.cookies)
        if cookies != self.entry.data.get("cookies"):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, "cookies": cookies},
            )

        return accounts
