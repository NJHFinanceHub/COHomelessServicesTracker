"""
SQLite helpers for the Denver Checkbook ingest.

Tiny, deliberately-narrow upsert helpers. No ORM. Idempotency keys are
called out in the docstrings — re-running the ingest is safe.

All functions take a `sqlite3.Connection`. Caller is responsible for
opening, committing, and closing.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from typing import Optional

CHECKBOOK_SOURCE_DATASET = "denver_checkbook:wnau-xrqi"


def upsert_recipient(con: sqlite3.Connection, legal_name: str) -> int:
    """Insert or return the existing recipient.id keyed on legal_name."""
    row = con.execute(
        "SELECT id FROM recipient WHERE legal_name = ?", (legal_name,)
    ).fetchone()
    if row:
        return int(row[0])
    cur = con.execute(
        "INSERT INTO recipient (legal_name, is_nonprofit) VALUES (?, 1)",
        (legal_name,),
    )
    return int(cur.lastrowid)


def upsert_agency(con: sqlite3.Connection, name: str, parent: str = "city") -> int:
    """Insert or return existing agency.id keyed on name. Parent defaults to 'city'."""
    row = con.execute("SELECT id FROM agency WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row[0])
    cur = con.execute(
        "INSERT INTO agency (name, parent) VALUES (?, ?)", (name, parent)
    )
    return int(cur.lastrowid)


def upsert_funding_source(
    con: sqlite3.Connection,
    name: str,
    source_type: str = "other",
    source_url: Optional[str] = None,
) -> int:
    """Insert or return existing funding_source.id keyed on name.

    The checkbook stores funding-source strings verbatim (e.g.
    'General Fund', 'Federal HUD CoC', 'Homelessness Resolution Fund').
    We trust the verbatim string for now; a curator can later edit the
    `type` and `legal_authority` columns.
    """
    row = con.execute(
        "SELECT id FROM funding_source WHERE name = ?", (name,)
    ).fetchone()
    if row:
        return int(row[0])
    cur = con.execute(
        "INSERT INTO funding_source (name, type, source_url) VALUES (?, ?, ?)",
        (name, source_type, source_url),
    )
    return int(cur.lastrowid)


def insert_payment(
    con: sqlite3.Connection,
    *,
    agency_id: int,
    recipient_id: int,
    payment_date: Optional[str],
    amount: float,
    fund_code: Optional[str],
    object_code: Optional[str],
    description: Optional[str],
    source_dataset: str,
    source_row_id: str,
) -> Optional[int]:
    """Insert a payment, idempotent on (source_dataset, source_row_id).

    Returns the new payment.id, or None if the row was already present.
    `payment_date` should be an ISO date string (YYYY-MM-DD); the schema
    stores it as TEXT.
    """
    try:
        cur = con.execute(
            """
            INSERT INTO payment (
                agency_id, recipient_id, payment_date, amount,
                fund_code, object_code, description,
                source_dataset, source_row_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agency_id,
                recipient_id,
                payment_date,
                amount,
                fund_code,
                object_code,
                description,
                source_dataset,
                source_row_id,
            ),
        )
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        # UNIQUE (source_dataset, source_row_id) — row already ingested
        return None


def log_fetch(
    con: sqlite3.Connection,
    *,
    source_name: str,
    url: str,
    http_status: Optional[int] = None,
    notes: Optional[str] = None,
    raw_payload: Optional[str] = None,
) -> int:
    """Append a row to source_fetch. `raw_payload` is hashed, not stored."""
    sha = (
        hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        if raw_payload is not None
        else None
    )
    cur = con.execute(
        """
        INSERT INTO source_fetch (source_name, fetched_at, url, http_status, sha256, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source_name,
            dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            url,
            http_status,
            sha,
            notes,
        ),
    )
    return int(cur.lastrowid)


# ----- Phase 1 helpers --------------------------------------------------

def normalize_iso_date(value: Optional[str]) -> Optional[str]:
    """Best-effort coerce Socrata calendar_date values to YYYY-MM-DD.

    Socrata's `calendar_date` is typically `YYYY-MM-DDTHH:MM:SS.SSS`. We
    truncate to the date component. Non-ISO inputs return None.
    """
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Already a date?
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def coerce_amount(value) -> float:
    """Coerce Socrata's number-as-string into a float; 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
