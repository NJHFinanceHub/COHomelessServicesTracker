"""Tests for the DB upsert helpers + the ingest-loop transform logic.

Uses in-memory SQLite. No network.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from etl.sources.denver_checkbook.db import (
    CHECKBOOK_SOURCE_DATASET,
    coerce_amount,
    insert_payment,
    log_fetch,
    normalize_iso_date,
    upsert_agency,
    upsert_funding_source,
    upsert_recipient,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


@pytest.fixture
def con() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA_PATH.read_text())
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


# ----- helper functions ------------------------------------------------

def test_normalize_iso_date():
    assert normalize_iso_date("2026-04-29T00:00:00.000") == "2026-04-29"
    assert normalize_iso_date("2026-04-29") == "2026-04-29"
    assert normalize_iso_date("") is None
    assert normalize_iso_date(None) is None
    assert normalize_iso_date("garbage") is None


def test_coerce_amount():
    assert coerce_amount("123.45") == 123.45
    assert coerce_amount(7) == 7.0
    assert coerce_amount(None) == 0.0
    assert coerce_amount("oops") == 0.0


# ----- upserts ---------------------------------------------------------

def test_upsert_recipient_is_idempotent(con):
    a = upsert_recipient(con, "Colorado Coalition for the Homeless")
    b = upsert_recipient(con, "Colorado Coalition for the Homeless")
    assert a == b
    n = con.execute("SELECT COUNT(*) FROM recipient").fetchone()[0]
    assert n == 1


def test_upsert_recipient_distinguishes_names(con):
    a = upsert_recipient(con, "Colorado Coalition for the Homeless")
    b = upsert_recipient(con, "Volunteers of America Colorado")
    assert a != b


def test_upsert_agency_defaults_to_city(con):
    aid = upsert_agency(con, "Housing Stability")
    parent = con.execute("SELECT parent FROM agency WHERE id = ?", (aid,)).fetchone()[0]
    assert parent == "city"


def test_upsert_funding_source_records_type_default(con):
    fid = upsert_funding_source(con, "General Fund")
    t = con.execute("SELECT type FROM funding_source WHERE id = ?", (fid,)).fetchone()[0]
    assert t == "other"


# ----- payment insert idempotency ---------------------------------------

def test_payment_insert_and_dedup(con):
    r = upsert_recipient(con, "Test Org")
    a = upsert_agency(con, "Test Dept")
    first = insert_payment(
        con,
        agency_id=a, recipient_id=r,
        payment_date="2026-01-15", amount=100.0,
        fund_code=None, object_code=None, description=None,
        source_dataset=CHECKBOOK_SOURCE_DATASET, source_row_id="row-1",
    )
    assert first is not None

    dup = insert_payment(
        con,
        agency_id=a, recipient_id=r,
        payment_date="2026-01-15", amount=100.0,
        fund_code=None, object_code=None, description=None,
        source_dataset=CHECKBOOK_SOURCE_DATASET, source_row_id="row-1",
    )
    assert dup is None  # same source_row_id → dedup

    other = insert_payment(
        con,
        agency_id=a, recipient_id=r,
        payment_date="2026-01-16", amount=50.0,
        fund_code=None, object_code=None, description=None,
        source_dataset=CHECKBOOK_SOURCE_DATASET, source_row_id="row-2",
    )
    assert other is not None and other != first

    total = con.execute("SELECT SUM(amount) FROM payment").fetchone()[0]
    assert total == 150.0


def test_log_fetch_writes_provenance_row(con):
    fid = log_fetch(
        con,
        source_name="denver_checkbook",
        url="https://example/resource.json",
        http_status=200,
        notes="test",
        raw_payload="hello",
    )
    row = con.execute(
        "SELECT source_name, url, http_status, sha256, notes FROM source_fetch WHERE id = ?",
        (fid,),
    ).fetchone()
    assert row[0] == "denver_checkbook"
    assert row[1] == "https://example/resource.json"
    assert row[2] == 200
    # sha256 of "hello"
    assert row[3] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert row[4] == "test"
