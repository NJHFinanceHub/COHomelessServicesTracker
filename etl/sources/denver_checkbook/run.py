"""
Phase 1 entry point — reserved.

Once the schema is validated against live data, this module will:
  1. Open the SQLite db at --db
  2. Resolve curated vendor seeds into `recipient` rows (idempotent insert)
  3. Pull all checkbook payments matching seed vendors since last run
  4. Insert into `payment` with (source_dataset, source_row_id) as the
     idempotency key
  5. Log the fetch in `source_fetch`

Phase 0 stub: no DB writes. Run scan.py instead.
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Denver Checkbook ETL (Phase 1, not yet active)")
    p.add_argument("--db", required=False, help="Path to SQLite DB (Phase 1+)")
    args = p.parse_args(argv)

    print("etl.sources.denver_checkbook.run is a Phase 1 placeholder.")
    print("Use `python -m etl.sources.denver_checkbook.scan --columns` to probe the dataset.")
    print(f"(args.db = {args.db})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
