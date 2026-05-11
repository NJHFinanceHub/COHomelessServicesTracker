"""Test ingest_for_seed with a fake Socrata client. No network.

Verifies: vendor cross-talk is rejected client-side, idempotent re-runs
don't double-count, and the per-seed stats reflect reality.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from etl.sources.denver_checkbook.run import (
    _build_where,
    _patterns_for_seed,
    ingest_for_seed,
)
from etl.sources.denver_checkbook.vendor_seeds import SEEDS, VendorSeed

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

PROBE = {
    "endpoint": "https://example/resource.json",
    "dataset_id": "wnau-xrqi",
    "columns": [
        {"fieldName": "payee", "name": "Payee", "dataTypeName": "text"},
        {"fieldName": "amount", "name": "Amount", "dataTypeName": "number"},
        {"fieldName": "paymentdate", "name": "PaymentDate", "dataTypeName": "calendar_date"},
        {"fieldName": "department", "name": "Department", "dataTypeName": "text"},
        {"fieldName": "fundingsourcedescription", "name": "FundingSourceDescription", "dataTypeName": "text"},
        {"fieldName": "expensecategory", "name": "ExpenseCategory", "dataTypeName": "text"},
        {"fieldName": "projectdescription", "name": "ProjectDescription", "dataTypeName": "text"},
        {"fieldName": "programarea", "name": "ProgramArea", "dataTypeName": "text"},
    ],
    "resolved": {
        "vendor_field": "payee",
        "amount_field": "amount",
        "date_field": "paymentdate",
    },
}


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.dataset = type("D", (), {"resource_url": "https://example/resource.json"})()

    def query(self, *, select=None, where=None, order=None, limit=None, max_rows=None):
        for r in self.rows:
            yield r


def _cch_seed():
    return next(s for s in SEEDS if s.canonical == "Colorado Coalition for the Homeless")


def _voa_seed():
    return next(s for s in SEEDS if s.canonical == "Volunteers of America Colorado")


@pytest.fixture
def con():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA_PATH.read_text())
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


def test_ingest_inserts_matched_rows(con):
    rows = [
        {
            "socrata_id": "row-1",
            "payee": "COLORADO COALITION FOR THE HOMELESS, INC.",
            "amount": "1000.00",
            "paymentdate": "2026-01-01T00:00:00.000",
            "department": "Housing Stability",
            "fundingsourcedescription": "Homelessness Resolution Fund",
            "expensecategory": "Contract Services",
            "projectdescription": "PSH operations",
            "programarea": "Permanent Supportive Housing",
        },
        {
            "socrata_id": "row-2",
            "payee": "Colorado Coalition for the Homeless",
            "amount": "250.50",
            "paymentdate": "2026-02-14T00:00:00.000",
            "department": "Housing Stability",
            "fundingsourcedescription": "General Fund",
            "expensecategory": "Grants",
        },
    ]
    stats = ingest_for_seed(
        con=con, client=FakeClient(rows), probe=PROBE,
        seed=_cch_seed(), since=None, max_rows=None,
    )
    assert stats["inserted"] == 2
    assert stats["duplicates"] == 0
    assert stats["rejected_no_match"] == 0
    total = con.execute("SELECT SUM(amount) FROM payment").fetchone()[0]
    assert total == pytest.approx(1250.50)


def test_ingest_rejects_cross_talk(con):
    # Server-side LIKE for "coalition for the homeless" can be loose; the
    # matcher should reject a row that doesn't actually belong to this seed.
    rows = [
        {
            "socrata_id": "row-x",
            "payee": "Acme Office Supplies",  # won't match the matcher
            "amount": "999",
            "paymentdate": "2026-01-01",
            "department": "Procurement",
        },
    ]
    stats = ingest_for_seed(
        con=con, client=FakeClient(rows), probe=PROBE,
        seed=_cch_seed(), since=None, max_rows=None,
    )
    assert stats["rejected_no_match"] == 1
    assert stats["inserted"] == 0
    n = con.execute("SELECT COUNT(*) FROM payment").fetchone()[0]
    assert n == 0


def test_ingest_dedups_on_rerun(con):
    rows = [
        {
            "socrata_id": "row-1",
            "payee": "Colorado Coalition for the Homeless",
            "amount": "1000.00",
            "paymentdate": "2026-01-01",
            "department": "Housing Stability",
        },
    ]
    a = ingest_for_seed(con=con, client=FakeClient(rows), probe=PROBE,
                       seed=_cch_seed(), since=None, max_rows=None)
    b = ingest_for_seed(con=con, client=FakeClient(rows), probe=PROBE,
                       seed=_cch_seed(), since=None, max_rows=None)
    assert a["inserted"] == 1 and a["duplicates"] == 0
    assert b["inserted"] == 0 and b["duplicates"] == 1
    n = con.execute("SELECT COUNT(*) FROM payment").fetchone()[0]
    assert n == 1


def test_ingest_skips_zero_amounts(con):
    rows = [
        {"socrata_id": "z1", "payee": "Colorado Coalition for the Homeless",
         "amount": "0", "paymentdate": "2026-01-01", "department": "HOST"},
        {"socrata_id": "z2", "payee": "Colorado Coalition for the Homeless",
         "amount": "", "paymentdate": "2026-01-02", "department": "HOST"},
    ]
    stats = ingest_for_seed(con=con, client=FakeClient(rows), probe=PROBE,
                            seed=_cch_seed(), since=None, max_rows=None)
    assert stats["rejected_no_amount"] == 2
    assert stats["inserted"] == 0


def test_ingest_handles_voa_aliases(con):
    rows = [
        {"socrata_id": "v1", "payee": "VOA Colorado", "amount": "100",
         "paymentdate": "2026-03-01", "department": "Housing Stability"},
    ]
    stats = ingest_for_seed(con=con, client=FakeClient(rows), probe=PROBE,
                            seed=_voa_seed(), since=None, max_rows=None)
    assert stats["inserted"] == 1


# ----- _build_where ---------------------------------------------------------

def test_build_where_ors_distinctive_and_aliases():
    seed = VendorSeed(
        canonical="Test Org",
        distinctive="st. francis center",
        aliases=["saint francis center", "st francis center"],
    )
    where = _build_where("payee", seed)
    # All three patterns should be OR'd in
    assert "st. francis center" in where
    assert "saint francis center" in where
    assert "st francis center" in where
    assert " OR " in where
    # Wrapped in parens for safe AND-composition later
    assert where.startswith("(") and where.endswith(")")


def test_build_where_no_aliases_still_works():
    seed = VendorSeed(canonical="Solo Org", distinctive="solo phrase", aliases=[])
    where = _build_where("payee", seed)
    assert "solo phrase" in where
    assert " OR " not in where  # only the distinctive


def test_patterns_for_seed_dedups_case_insensitive():
    seed = VendorSeed(
        canonical="Dedup Org",
        distinctive="acme corp",
        aliases=["ACME Corp", "acme corp", "Acme  Corp"],  # case + whitespace variants
    )
    patterns = _patterns_for_seed(seed)
    assert len(patterns) == 1
    assert patterns[0].lower() == "acme corp"


def test_build_where_escapes_single_quotes():
    seed = VendorSeed(
        canonical="O'Quote Org",
        distinctive="o'reilly center",
        aliases=[],
    )
    where = _build_where("payee", seed)
    # SQL-safe: the literal must double the apostrophe so SoQL doesn't break
    assert "o''reilly center" in where
