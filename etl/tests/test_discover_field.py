"""Offline tests for scan.discover_field."""
from __future__ import annotations

from etl.sources.denver_checkbook.scan import (
    AMOUNT_FIELD_CANDIDATES,
    DATE_FIELD_CANDIDATES,
    VENDOR_FIELD_CANDIDATES,
    discover_field,
)


def _cols(*names: str) -> list[dict]:
    return [{"fieldName": n, "name": n.replace("_", " ").title(), "dataTypeName": "text"} for n in names]


def test_exact_match_wins():
    cols = _cols("payee", "amount", "payment_date", "fund", "object")
    assert discover_field(cols, VENDOR_FIELD_CANDIDATES) == "payee"
    assert discover_field(cols, AMOUNT_FIELD_CANDIDATES) == "amount"
    assert discover_field(cols, DATE_FIELD_CANDIDATES) == "payment_date"


def test_case_insensitive_fallback():
    # Field names that don't match exactly but match case-insensitively
    cols = _cols("Payee", "Amount", "Date")
    assert discover_field(cols, ["payee"]) == "Payee"
    assert discover_field(cols, ["amount"]) == "Amount"


def test_partial_substring_fallback():
    # Real-world quirk: a column called payee_full_name should still resolve
    cols = _cols("payee_full_name", "expenditure_amount_usd", "post_date_iso")
    assert discover_field(cols, VENDOR_FIELD_CANDIDATES) == "payee_full_name"
    assert discover_field(cols, AMOUNT_FIELD_CANDIDATES) == "expenditure_amount_usd"
    assert discover_field(cols, DATE_FIELD_CANDIDATES) == "post_date_iso"


def test_returns_none_when_no_candidate_present():
    cols = _cols("foo", "bar", "baz")
    assert discover_field(cols, VENDOR_FIELD_CANDIDATES) is None


def test_first_candidate_priority_over_later():
    # If both 'payee' and 'vendor_name' exist, 'payee' (listed first) wins.
    cols = _cols("vendor_name", "payee")
    assert discover_field(cols, VENDOR_FIELD_CANDIDATES) == "payee"
