"""Event entity that fires once for every new MyEdenred transaction."""
from __future__ import annotations

from typing import Callable

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .api.transaction import KINDS
from .const import DOMAIN
from .entity import MyEdenredCardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Add one transaction event entity per card (only when transactions are enabled)."""
    runtime_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not runtime_data or not config_entry.data.get("includeTransactions"):
        return
    coordinator = runtime_data["coordinator"]
    async_add_entities(
        [MyEdenredTransactionEvent(card, coordinator) for card in runtime_data["cards"]]
    )


class MyEdenredTransactionEvent(MyEdenredCardEntity, EventEntity):
    """Fires purchase / top_up / refund / other for each transaction seen for the first time.

    Transactions already in the list when Home Assistant starts are treated as
    seen, so a restart never replays old purchases.
    """

    _attr_event_types = KINDS
    _attr_icon = "mdi:credit-card-fast-outline"

    def __init__(self, card, coordinator) -> None:
        super().__init__(card, coordinator, "transaction")
        self._seen: set | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._seen = {t.key for t in self.transactions}

    @callback
    def _handle_coordinator_update(self) -> None:
        transactions = self.transactions
        if self._seen is None:
            self._seen = {t.key for t in transactions}
            return
        new = [t for t in transactions if t.key not in self._seen]
        for transaction in reversed(new):  # oldest first
            self._trigger_event(transaction.kind, transaction.as_dict())
            self.async_write_ha_state()
        self._seen = {t.key for t in transactions}
