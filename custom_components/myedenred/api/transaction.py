"""Transaction Class."""
from __future__ import annotations

from datetime import datetime
import re

KIND_PURCHASE = "purchase"
KIND_TOP_UP = "top_up"
KIND_REFUND = "refund"
KIND_OTHER = "other"
KINDS = [KIND_PURCHASE, KIND_TOP_UP, KIND_REFUND, KIND_OTHER]

# Purchases come as "Compra: <merchant, padded to 20 characters><location>",
# e.g. "Compra: CAFE CENTRAL        PORTO" or
# "Compra: MERCEARIA EXEMPLO   4000-123 PORTO".
MERCHANT_WIDTH = 20
_POSTCODE = re.compile(r"^\d{4}-\d{3}\s*")
_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")


class Transaction:
    """Represents a MyEdenred account transaction."""

    def __init__(self, transaction):
        self._data = transaction

    @property
    def date(self):
        return self._data["transactionDate"]

    @property
    def name(self):
        return self._data["transactionName"]

    @property
    def amount(self) -> float:
        return float(self._data["amount"])

    @property
    def key(self) -> tuple:
        """Identify a transaction across updates."""
        return (self._data.get("transactionDate"), self._data.get("transactionName"), self._data.get("amount"))

    @property
    def timestamp(self) -> datetime | None:
        """Return the transaction time as an aware datetime, if it can be parsed."""
        raw = self._data.get("transactionDate")
        if not raw:
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except (TypeError, ValueError):
                continue
        try:
            return datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            return None

    @property
    def kind(self) -> str:
        """Return purchase, top_up, refund or other."""
        name = (self._data.get("transactionName") or "").strip().lower()
        if name.startswith("compra"):
            return KIND_PURCHASE
        if self.amount > 0:
            if "transfer" in name or "carregamento" in name:
                return KIND_TOP_UP
            return KIND_REFUND
        return KIND_OTHER

    @property
    def description(self) -> str:
        """Return the text after the "Compra:"-style prefix, or the whole name."""
        name = self._data.get("transactionName") or ""
        if self.kind == KIND_PURCHASE and ":" in name:
            name = name.split(":", 1)[1]
        return " ".join(name.split())

    def _purchase_body(self) -> str | None:
        name = self._data.get("transactionName") or ""
        if self.kind != KIND_PURCHASE or ":" not in name:
            return None
        body = name.split(":", 1)[1]
        return body[1:] if body.startswith(" ") else body

    @property
    def merchant(self) -> str | None:
        """Return the merchant of a purchase."""
        body = self._purchase_body()
        if body is None:
            return None
        return body[:MERCHANT_WIDTH].strip() or None

    @property
    def location(self) -> str | None:
        """Return the town of a purchase, without the postcode."""
        body = self._purchase_body()
        if body is None or len(body) <= MERCHANT_WIDTH:
            return None
        return _POSTCODE.sub("", body[MERCHANT_WIDTH:].strip()) or None

    def as_dict(self) -> dict:
        """Return the readable fields used by the new entities."""
        when = self.timestamp
        return {
            "date": when.isoformat() if when else self.date,
            "kind": self.kind,
            "amount": self.amount,
            "merchant": self.merchant,
            "location": self.location,
            "description": self.description,
        }
