"""Platform for the MyEdenred card balance sensors."""
from __future__ import annotations

from typing import Any, Callable, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.card import Card
from .const import ATTRIBUTION, DEFAULT_ICON, DOMAIN, UNIT_OF_MEASUREMENT
from .coordinator import MyEdenredDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up all card sensors for the config entry."""
    runtime_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not runtime_data:
        raise ConfigEntryNotReady("MyEdenred runtime data is not available")

    coordinator = runtime_data["coordinator"]
    async_add_entities(
        [
            MyEdenredSensor(card, config_entry, coordinator)
            for card in runtime_data["cards"]
        ],
        update_before_add=False,
    )


class MyEdenredSensor(
    CoordinatorEntity[MyEdenredDataUpdateCoordinator], SensorEntity
):
    """Represent the balance and transactions for one Edenred card."""

    def __init__(
        self,
        card: Card,
        config_entry: ConfigEntry,
        coordinator: MyEdenredDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._card = card
        self._config_entry = config_entry
        self._attr_icon = DEFAULT_ICON
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UNIT_OF_MEASUREMENT

    @property
    def name(self) -> str:
        """Return the entity name."""
        return f"Edenred Card {self._card.number}"

    @property
    def unique_id(self) -> str:
        """Return a stable entity identifier."""
        return f"{DOMAIN}-{self._card.id}".lower()

    @property
    def native_value(self) -> float | None:
        """Return the balance from the most recent shared update."""
        account = self.coordinator.data.get(self._card.id)
        return account.availableBalance if account else None

    @property
    def attribution(self) -> str:
        """Return the data attribution."""
        return ATTRIBUTION

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return card metadata and, when enabled, transactions."""
        attributes: Dict[str, Any] = {
            "ownerName": self._card.ownerName,
            "cardStatus": self._card.status,
            "cardNumber": self._card.number,
            "transactions": [],
        }
        if self._config_entry.data["includeTransactions"]:
            account = self.coordinator.data.get(self._card.id)
            attributes["transactions"] = (
                [
                    {
                        "date": transaction.date,
                        "name": transaction.name,
                        "amount": transaction.amount,
                    }
                    for transaction in account.movementList
                ]
                if account
                else []
            )
        return attributes
