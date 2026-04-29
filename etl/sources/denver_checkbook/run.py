"""
Phase 1 entry point — refuses to run without a verified column probe.

Phase 1 will:
  1. Open the SQLite db at --db
  2. Resolve curated vendor seeds into `recipient` rows (idempotent insert
     keyed on legal_name)
  3. Pull all checkbook payments matching seed vendors since last run
  4. Insert into `payment` with (source_dataset, source_row_id) as the
     idempotency key
  5. Log the fetch in `source_fetch`

Hard precondition: `data/raw/checkbook_columns.json` must exist and resolve
non-null vendor_field/amount_field/date_field. Generate it by running:

    python -m etl.sources.denver_checkbook.scan --columns

from a host with internet egress, then commit the file. This prevents the
ingest from silently binding to guessed column names.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COLUMNS_PATH = Path("data/raw/checkbook_columns.json")


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
            "Inspect the column list in that file and either: (a) add the real\n"
            "field name to the appropriate _CANDIDATES list in scan.py and\n"
            "re-run the probe, or (b) hand-edit the resolved.<field> entry.",
            file=sys.stderr,
        )
        sys.exit(2)
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Denver Checkbook ETL (Phase 1)")
    p.add_argument("--db", required=True, help="Path to SQLite DB")
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
    )

    if args.dry_run:
        print("--dry-run set; not writing to DB.")
        return 0

    # The actual ingest is intentionally not implemented yet. It is gated on
    # the user reviewing the new-candidates CSV from `scan.py --new-candidates`
    # and confirming the seed list before any DB writes.
    print(
        "Phase 1 ingest not yet wired. Next step: review\n"
        "  data/interim/new_candidates_*.csv\n"
        "expand etl/sources/denver_checkbook/vendor_seeds.SEEDS as needed,\n"
        "then implement the (recipient, payment, source_fetch) inserts here."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
