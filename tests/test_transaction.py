"""Tests for the readable transaction fields (pure Python, no Home Assistant)."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "myedenred_transaction",
    Path(__file__).resolve().parents[1] / "custom_components/myedenred/api/transaction.py",
)
tx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tx)


def make(name, amount, date="2026-01-15T12:30:00.123+0000"):
    return tx.Transaction({"transactionDate": date, "transactionName": name, "amount": amount})


def test_purchase_with_padded_merchant_and_town():
    t = make("Compra: CAFE CENTRAL        PORTO", -4.5)
    assert t.kind == tx.KIND_PURCHASE
    assert t.merchant == "CAFE CENTRAL"
    assert t.location == "PORTO"
    assert t.description == "CAFE CENTRAL PORTO"


def test_purchase_merchant_filling_the_column_and_postcode():
    assert make("Compra: RESTAURANTE EXEMPLOBRAGA", -12.0).merchant == "RESTAURANTE EXEMPLOB"
    t = make("Compra: MERCEARIA EXEMPLO   4000-123 PORTO", -20.0)
    assert (t.merchant, t.location) == ("MERCEARIA EXEMPLO", "PORTO")


def test_top_up_refund_and_other():
    assert make("Transferência Bancária", 200.0).kind == tx.KIND_TOP_UP
    assert make("Devolução: LOJA", 5.0).kind == tx.KIND_REFUND
    other = make("Comissão", -1.0)
    assert other.kind == tx.KIND_OTHER
    assert other.merchant is None and other.location is None


def test_dates():
    assert make("x", -1).timestamp.isoformat() == "2026-01-15T12:30:00.123000+00:00"
    assert make("x", -1, "2026-01-15T12:30:00+0000").timestamp.isoformat() == "2026-01-15T12:30:00+00:00"
    bad = make("x", -1, "not a date")
    assert bad.timestamp is None
    assert bad.as_dict()["date"] == "not a date"


def test_legacy_fields_unchanged():
    t = make("Compra: CAFE CENTRAL        PORTO", -4.5)
    assert (t.date, t.name, t.amount) == (
        "2026-01-15T12:30:00.123+0000",
        "Compra: CAFE CENTRAL        PORTO",
        -4.5,
    )
