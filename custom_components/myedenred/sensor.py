"""Platform for sensor integration."""
from __future__ import annotations
from typing import Any
import aiohttp
import logging

from datetime import timedelta
from typing import Any, Callable, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api.myedenred import (
    MY_EDENRED,
    MyEdenredAuthError,
    MyEdenredError,
)
from .api.card import Card
from .const import (
    DOMAIN,
    DEFAULT_ICON,
    UNIT_OF_MEASUREMENT,
    ATTRIBUTION
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Time between updating data from API
SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_entry(hass: HomeAssistant, 
                            config_entry: ConfigEntry, 
                            async_add_entities: Callable):
    """Setup sensor platform."""
    runtime_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not runtime_data:
        raise ConfigEntryNotReady("MyEdenred runtime data is not available")

    sensors = [
        MyEdenredSensor(
            card,
            runtime_data["api"],
            config_entry,
            runtime_data["accounts"].get(card.id),
        )
        for card in runtime_data["cards"]
    ]
    async_add_entities(sensors, update_before_add=False)


class MyEdenredSensor(SensorEntity):
    """Representation of a MyEdenred Card (Sensor)."""

    def __init__(
        self,
        card: Card,
        api: MY_EDENRED,
        config_entry: ConfigEntry,
        account: Any,
    ):
        super().__init__()
        self._card = card
        self._api = api
        self._config_entry = config_entry
        self._transactions = None

        self._icon = DEFAULT_ICON
        self._unit_of_measurement = UNIT_OF_MEASUREMENT
        self._device_class = SensorDeviceClass.MONETARY
        self._state_class = SensorStateClass.TOTAL
        self._state = None
        self._available = True
        if account:
            self._apply_account(account)
        
    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"Edenred Card {self._card.number}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}-{self._card.id}".lower()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> float:
        return self._state

    @property
    def device_class(self):
        return self._device_class

    @property
    def state_class(self):
        return self._state_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        return self._icon

    @property
    def attribution(self):
        return ATTRIBUTION

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            "ownerName": self._card.ownerName,
            "cardStatus": self._card.status,
            "cardNumber": self._card.number,
            "transactions": self._transactions
        }

    def _apply_account(self, account) -> None:
        """Apply account data to the entity state."""
        self._state = account.availableBalance
        if self._config_entry.data["includeTransactions"]:
            transactions = []
            for transaction in account.movementList:
                transactions.append({
                    "date": transaction.date,
                    "name": transaction.name,
                    "amount": transaction.amount,
                })
            self._transactions = transactions

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
           This is the only method that should fetch new data for Home Assistant.
        """
        api = self._api
        config = self._config_entry.data
        card = self._card
        
        try:            
            token = config.get("token")
            if (token):
                account = await api.getAccountDetails(card.id, token)
                if api.cookies != config.get("cookies"):
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data={
                            **config,
                            "cookies": api.cookies,
                        },
                    )
                self._apply_account(account)
                self._available = True

        except MyEdenredAuthError as err:
            self._available = False
            raise ConfigEntryAuthFailed("MyEdenred token expired") from err
        except (aiohttp.ClientError, MyEdenredError) as err:
            self._available = False
            _LOGGER.exception("Error updating data from DGEG API. %s", err)            
