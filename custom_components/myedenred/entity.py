"""Shared helpers for the per-card MyEdenred entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.card import Card
from .api.transaction import Transaction
from .const import DOMAIN
from .coordinator import MyEdenredDataUpdateCoordinator


def card_device_info(card: Card) -> DeviceInfo:
    """Group every entity of one card under one device."""
    number = str(card.number or "")
    return DeviceInfo(
        identifiers={(DOMAIN, str(card.id))},
        name=f"Edenred card {number[-4:]}" if number else "Edenred card",
        manufacturer="Edenred",
        model="MyEdenred card",
    )


def newest_first(transactions: list[Transaction]) -> list[Transaction]:
    """Sort transactions newest first; unparsable dates go last."""
    def sort_key(transaction: Transaction) -> float:
        when = transaction.timestamp
        return when.timestamp() if when else float("-inf")

    return sorted(transactions, key=sort_key, reverse=True)


class MyEdenredCardEntity(CoordinatorEntity[MyEdenredDataUpdateCoordinator]):
    """Base for the extra entities of one card."""

    _attr_has_entity_name = True

    def __init__(self, card: Card, coordinator: MyEdenredDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._card = card
        self._attr_translation_key = key
        self._attr_unique_id = f"{DOMAIN}-{card.id}-{key}".lower()
        self._attr_device_info = card_device_info(card)

    @property
    def transactions(self) -> list[Transaction]:
        """Return this card's transactions, newest first."""
        account = (self.coordinator.data or {}).get(self._card.id)
        return newest_first(account.movementList) if account else []

    @property
    def current_card(self) -> Card:
        """Return the card as refreshed by the coordinator, if available."""
        for card in getattr(self.coordinator, "cards", None) or []:
            if card.id == self._card.id:
                return card
        return self._card
