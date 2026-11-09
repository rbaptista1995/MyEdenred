"""Platform for the MyEdenred card balance sensors."""
from __future__ import annotations

from typing import Any, Callable, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api.card import Card
from .api.transaction import KIND_PURCHASE, KIND_REFUND, KIND_TOP_UP
from .const import ATTRIBUTION, DEFAULT_ICON, DOMAIN, UNIT_OF_MEASUREMENT
from .coordinator import MyEdenredDataUpdateCoordinator
from .entity import MyEdenredCardEntity, card_device_info


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
    entities: list[SensorEntity] = []
    for card in runtime_data["cards"]:
        # Unchanged balance sensor (same name, unique_id and attributes as before).
        entities.append(MyEdenredSensor(card, config_entry, coordinator))
        entities.append(MyEdenredCardStatusSensor(card, coordinator))
        if config_entry.data.get("includeTransactions"):
            entities.extend(
                [
                    MyEdenredLastTransactionSensor(card, coordinator),
                    MyEdenredLastTransactionTimeSensor(card, coordinator),
                    MyEdenredSpentThisMonthSensor(card, coordinator),
                    MyEdenredLastTopUpSensor(card, coordinator),
                ]
            )
    async_add_entities(entities, update_before_add=False)


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
        self._attr_device_info = card_device_info(card)

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


class MyEdenredCardStatusSensor(MyEdenredCardEntity, SensorEntity):
    """Card status as reported by MyEdenred (e.g. ACTIVE)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:credit-card-check-outline"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "card_status")

    @property
    def native_value(self) -> str | None:
        status = self.current_card.status
        return str(status).lower() if status is not None else None


class MyEdenredLastTransactionSensor(MyEdenredCardEntity, SensorEntity):
    """Amount of the most recent transaction, with readable details."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = UNIT_OF_MEASUREMENT
    _attr_icon = "mdi:receipt-text-outline"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "last_transaction")

    @property
    def native_value(self) -> float | None:
        transactions = self.transactions
        return transactions[0].amount if transactions else None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        transactions = self.transactions
        return transactions[0].as_dict() if transactions else {}


class MyEdenredLastTransactionTimeSensor(MyEdenredCardEntity, SensorEntity):
    """When the most recent transaction happened."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "last_transaction_time")

    @property
    def native_value(self):
        transactions = self.transactions
        return transactions[0].timestamp if transactions else None


class MyEdenredSpentThisMonthSensor(MyEdenredCardEntity, SensorEntity):
    """Purchases minus refunds in the current calendar month (local time)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = UNIT_OF_MEASUREMENT
    _attr_icon = "mdi:cart-outline"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "spent_this_month")

    def _this_month(self):
        now = dt_util.now()
        for transaction in self.transactions:
            when = transaction.timestamp
            if when is None or transaction.kind not in (KIND_PURCHASE, KIND_REFUND):
                continue
            local = dt_util.as_local(when)
            if (local.year, local.month) == (now.year, now.month):
                yield transaction

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return round(-sum(t.amount for t in self._this_month()), 2)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {"transactions": len(list(self._this_month()))}


class MyEdenredLastTopUpSensor(MyEdenredCardEntity, SensorEntity):
    """Amount and date of the most recent top-up."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = UNIT_OF_MEASUREMENT
    _attr_icon = "mdi:cash-plus"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "last_top_up")

    def _last(self):
        return next((t for t in self.transactions if t.kind == KIND_TOP_UP), None)

    @property
    def native_value(self) -> float | None:
        last = self._last()
        return last.amount if last else None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        last = self._last()
        if not last:
            return {}
        when = last.timestamp
        return {"date": when.isoformat() if when else last.date}
