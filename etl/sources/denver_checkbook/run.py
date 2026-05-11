"""
Phase 1: real Denver Checkbook ingest.

Reads the verified column map at `data/raw/checkbook_columns.json`,
queries Socrata once per curated seed (server-side substring filter on
the distinctive phrase), and inserts matching payments idempotently.

The query strategy is intentionally per-seed-narrow:
  - The seed list is small (~30) and queries are cheap.
  - A single OR-mega-where would exceed Socrata's URL length limits
    and is harder to debug when one term silently breaks.
  - Idempotency on (source_dataset, source_row_id) means
    re-running over an overlapping window is safe.

Refuses to run without the column-map artifact; exit 2 with a clear
error if it's missing.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

from .client import SocrataClient
from .db import (
    CHECKBOOK_SOURCE_DATASET,
    coerce_amount,
    insert_payment,
    log_fetch,
    normalize_iso_date,
    upsert_agency,
    upsert_funding_source,
    upsert_recipient,
)
from .entity_resolution import match_vendor
from .vendor_seeds import SEEDS, VendorSeed

COLUMNS_PATH = Path("data/raw/checkbook_columns.json")


# ----- column probe -----------------------------------------------------

def _require_columns_probe() -> dict:
    if not COLUMNS_PATH.exists():
        print(
            f"ERROR: {COLUMNS_PATH} is missing.\n"
            "Run `python -m etl.sources.denver_checkbook.scan --columns` from\n"
            "a host with internet egress and commit the resulting file before\n"
            "re-running this ingest.",
            file=sys.stderr,
        )
        sys.exit(2)
    payload = json.loads(COLUMNS_PATH.read_text())
    resolved = payload.get("resolved", {})
    missing = [k for k in ("vendor_field", "amount_field", "date_field") if not resolved.get(k)]
    if missing:
        print(
            f"ERROR: {COLUMNS_PATH} is present but missing resolved fields: {missing}.\n"
            "Inspect the column list and either add the real field name to\n"
            "the appropriate _CANDIDATES list in scan.py and re-run the\n"
            "probe, or hand-edit the resolved.<field> entry.",
            file=sys.stderr,
        )
        sys.exit(2)
    return payload


# ----- query building ---------------------------------------------------

def _sql_escape_literal(s: str) -> str:
    """Escape a single-quoted SoQL literal — double the single quotes."""
    return s.replace("'", "''")


def _patterns_for_seed(seed: VendorSeed) -> list[str]:
    """Distinctive + aliases, whitespace-normalized, deduped, non-empty.

    Used as the OR'd substring patterns for the server-side LIKE filter.
    Each pattern is later wrapped in % and case-folded by SoQL.
    """
    raw = [seed.distinctive, *seed.aliases]
    out: list[str] = []
    seen: set[str] = set()
    for p in raw:
        if not p:
            continue
        clean = " ".join(p.split())  # collapse internal whitespace
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _build_where(vendor_field: str, seed: VendorSeed) -> str:
    """Server-side filter: OR across (distinctive + each alias).

    This keeps the server-side filter as permissive as the client-side
    matcher (which knows aliases). A previous version only OR'd the
    distinctive phrase, which silently dropped recipients whose checkbook
    spelling differs from our distinctive (e.g. checkbook says "Saint
    Francis Center" but our distinctive is "St. Francis Center").
    """
    patterns = _patterns_for_seed(seed)
    clauses = [
        f"upper({vendor_field}) like upper('%{_sql_escape_literal(p)}%')"
        for p in patterns
    ]
    return "(" + " OR ".join(clauses) + ")"


def _select_clause(probe: dict) -> str:
    """A $select that pulls the standard payment columns plus :id for idempotency.

    We pull a fixed set of columns rather than `*` so the wire format is
    stable across dataset additions. Caller may decide to read more.
    """
    resolved = probe["resolved"]
    available = {c["fieldName"] for c in probe["columns"]}
    cols = [
        ":id AS socrata_id",
        resolved["vendor_field"],
        resolved["amount_field"],
        resolved["date_field"],
    ]
    # Useful extras when present
    for opt in ("department", "fundingsourcedescription", "expensecategory",
                "projectdescription", "programarea", "year"):
        if opt in available:
            cols.append(opt)
    return ", ".join(cols)


# ----- ingest loop ------------------------------------------------------

def ingest_for_seed(
    *,
    con: sqlite3.Connection,
    client: SocrataClient,
    probe: dict,
    seed: VendorSeed,
    since: str | None,
    max_rows: int | None,
) -> dict:
    """Pull and persist payments for one seed. Returns stats dict."""
    vendor_field = probe["resolved"]["vendor_field"]
    amount_field = probe["resolved"]["amount_field"]
    date_field = probe["resolved"]["date_field"]

    where = _build_where(vendor_field, seed)
    if since:
        where = f"({where}) AND {date_field} >= '{_sql_escape_literal(since)}'"
    select = _select_clause(probe)

    inserted = 0
    duplicates = 0
    rejected_no_match = 0
    rejected_no_amount = 0
    rows_seen = 0

    for row in client.query(
        select=select,
        where=where,
        order=f"{date_field} DESC",
        max_rows=max_rows,
    ):
        rows_seen += 1

        # Confirm match client-side so a loose server-side LIKE can't introduce
        # cross-talk between similarly-named orgs. The matcher's whole-token
        # logic is the source of truth.
        raw_vendor = (row.get(vendor_field) or "").strip()
        m = match_vendor(raw_vendor)
        if not m or m.seed.canonical != seed.canonical:
            rejected_no_match += 1
            continue

        amount = coerce_amount(row.get(amount_field))
        if amount == 0.0:
            # $0 entries exist (voids, adjustments). Keep them if you want
            # full audit trail; skip them here so per-recipient totals don't
            # get noisy on a UI. Adjust later if a curator objects.
            rejected_no_amount += 1
            continue

        recipient_id = upsert_recipient(con, seed.canonical)
        department = (row.get("department") or "").strip() or "(unspecified)"
        agency_id = upsert_agency(con, department, parent="city")

        funding_name = (row.get("fundingsourcedescription") or "").strip()
        if funding_name:
            upsert_funding_source(con, funding_name)

        socrata_id = str(row.get("socrata_id") or "").strip()
        if not socrata_id:
            # Fall back: hash the row tuple. Lossy but deterministic.
            socrata_id = f"hash::{abs(hash((seed.canonical, row.get(date_field), amount)))}"

        new_id = insert_payment(
            con,
            agency_id=agency_id,
            recipient_id=recipient_id,
            payment_date=normalize_iso_date(row.get(date_field)),
            amount=amount,
            fund_code=funding_name or None,
            object_code=(row.get("expensecategory") or None),
            description=(row.get("projectdescription") or row.get("programarea") or None),
            source_dataset=CHECKBOOK_SOURCE_DATASET,
            source_row_id=socrata_id,
        )
        if new_id is None:
            duplicates += 1
        else:
            inserted += 1

    return {
        "canonical": seed.canonical,
        "rows_seen": rows_seen,
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected_no_match": rejected_no_match,
        "rejected_no_amount": rejected_no_amount,
    }


def run_ingest(
    *,
    db_path: Path,
    since: str | None = None,
    max_rows_per_seed: int | None = None,
    seeds: Iterable[VendorSeed] | None = None,
) -> dict:
    """Top-level ingest. Returns aggregate stats."""
    probe = _require_columns_probe()
    seeds = list(seeds if seeds is not None else SEEDS)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON")

    client = SocrataClient()
    log_fetch(
        con,
        source_name="denver_checkbook",
        url=client.dataset.resource_url,
        notes=f"phase-1 ingest start; seeds={len(seeds)} since={since}",
    )
    con.commit()

    overall = {"per_seed": [], "totals": {"inserted": 0, "duplicates": 0, "rows_seen": 0}}
    for seed in seeds:
        stats = ingest_for_seed(
            con=con,
            client=client,
            probe=probe,
            seed=seed,
            since=since,
            max_rows=max_rows_per_seed,
        )
        con.commit()
        overall["per_seed"].append(stats)
        overall["totals"]["inserted"] += stats["inserted"]
        overall["totals"]["duplicates"] += stats["duplicates"]
        overall["totals"]["rows_seen"] += stats["rows_seen"]
        print(
            f"  {seed.canonical}: rows_seen={stats['rows_seen']} "
            f"inserted={stats['inserted']} dupes={stats['duplicates']} "
            f"no_match={stats['rejected_no_match']} no_amount={stats['rejected_no_amount']}"
        )

    log_fetch(
        con,
        source_name="denver_checkbook",
        url=client.dataset.resource_url,
        notes=(
            f"phase-1 ingest end; inserted={overall['totals']['inserted']} "
            f"dupes={overall['totals']['duplicates']} "
            f"rows_seen={overall['totals']['rows_seen']}"
        ),
    )
    con.commit()
    con.close()
    return overall


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Denver Checkbook ETL (Phase 1)")
    p.add_argument("--db", required=True, help="Path to SQLite DB")
    p.add_argument("--since", default=None,
                   help="Only ingest rows with date_field >= this ISO date (YYYY-MM-DD)")
    p.add_argument("--max-rows-per-seed", type=int, default=None,
                   help="Cap rows per seed (mostly for development)")
    p.add_argument("--dry-run", action="store_true",
                   help="Resolve fields and print plan; do not write to DB")
    args = p.parse_args(argv)

    probe = _require_columns_probe()
    resolved = probe["resolved"]
    print(
        f"Using columns from {COLUMNS_PATH}:\n"
        f"  vendor_field = {resolved['vendor_field']}\n"
        f"  amount_field = {resolved['amount_field']}\n"
        f"  date_field   = {resolved['date_field']}\n"
        f"  fetched_at   = {probe.get('fetched_at')}\n"
        f"Seeds: {len(SEEDS)}\n"
        f"Since: {args.since or '(none)'}\n"
    )

    if args.dry_run:
        print("--dry-run set; not writing to DB.")
        return 0

    overall = run_ingest(
        db_path=Path(args.db),
        since=args.since,
        max_rows_per_seed=args.max_rows_per_seed,
    )
    t = overall["totals"]
    print(f"\nDone. inserted={t['inserted']}  duplicates={t['duplicates']}  rows_seen={t['rows_seen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
