"""
Phase 0 / pre-Phase-1 scan tool.

Prints (does not persist) a sample of the Denver Checkbook dataset and a
summary of what fraction of payments matched our curated nonprofit seed
list. The point is to verify two things before we commit to the schema:

  1. The real column names on the live dataset.
  2. Whether our entity-resolution heuristics catch the obvious nonprofits
     and don't catastrophically over-match.

Usage:
    python -m etl.sources.denver_checkbook.scan --rows 200
    python -m etl.sources.denver_checkbook.scan --vendor-counts --rows 5000
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List

from .client import SocrataClient
from .entity_resolution import match_vendor


# Heuristic candidates for the "vendor name" field on the dataset. We discover
# the real one at runtime via the metadata endpoint and pick the first match.
VENDOR_FIELD_CANDIDATES = [
    "vendor_name",
    "payee_name",
    "vendor",
    "payee",
    "supplier_name",
    "company_name",
]
AMOUNT_FIELD_CANDIDATES = [
    "payment_amount",
    "amount",
    "check_amount",
    "expenditure_amount",
    "warrant_amount",
]
DATE_FIELD_CANDIDATES = [
    "payment_date",
    "check_date",
    "warrant_date",
    "transaction_date",
    "post_date",
    "date",
]


def discover_field(columns: List[Dict[str, str]], candidates: List[str]) -> str | None:
    field_names = {c["fieldName"]: c for c in columns}
    for cand in candidates:
        if cand in field_names:
            return cand
    # Fallback: case-insensitive / partial match
    lowered = {fn.lower(): fn for fn in field_names}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
        for fn_low, fn in lowered.items():
            if cand.lower() in fn_low:
                return fn
    return None


def cmd_columns(client: SocrataClient) -> None:
    cols = client.columns()
    print(f"Dataset has {len(cols)} columns:")
    for c in cols:
        print(f"  {c['fieldName']:40s}  {c['dataTypeName']:15s}  {c['name']}")
    print()
    last = client.last_updated()
    if last:
        print(f"rowsUpdatedAt (epoch): {last}")


def cmd_sample(client: SocrataClient, rows: int) -> None:
    print(f"Fetching first {rows} rows...")
    rows_out = list(client.query(limit=min(rows, 1000), max_rows=rows))
    print(f"Got {len(rows_out)} rows. First row keys:")
    if rows_out:
        print(json.dumps(sorted(rows_out[0].keys()), indent=2))
        print("\nFirst 3 rows (full):")
        for r in rows_out[:3]:
            print(json.dumps(r, indent=2, default=str))


def cmd_vendor_counts(client: SocrataClient, rows: int) -> None:
    cols = client.columns()
    vendor_field = discover_field(cols, VENDOR_FIELD_CANDIDATES)
    amount_field = discover_field(cols, AMOUNT_FIELD_CANDIDATES)
    date_field = discover_field(cols, DATE_FIELD_CANDIDATES)
    print(f"Discovered fields: vendor={vendor_field}  amount={amount_field}  date={date_field}")
    if not vendor_field:
        print("ERROR: could not find a vendor-name column. Re-run with --columns to inspect.")
        sys.exit(2)

    print(f"Streaming {rows} rows ordered by {date_field or ':id'} desc...")
    order_clause = f"{date_field} DESC" if date_field else None
    counts: Counter[str] = Counter()
    totals: Dict[str, float] = defaultdict(float)
    matched = 0
    matched_totals: Dict[str, float] = defaultdict(float)
    matched_counts: Counter[str] = Counter()

    for r in client.query(order=order_clause, limit=1000, max_rows=rows):
        v = (r.get(vendor_field) or "").strip()
        if not v:
            continue
        counts[v] += 1
        amt_raw = r.get(amount_field) if amount_field else None
        try:
            amt = float(amt_raw) if amt_raw is not None else 0.0
        except (TypeError, ValueError):
            amt = 0.0
        totals[v] += amt

        m = match_vendor(v)
        if m:
            matched += 1
            matched_counts[m.seed.canonical] += 1
            matched_totals[m.seed.canonical] += amt

    total_rows = sum(counts.values())
    print()
    print(f"Scanned {total_rows:,} payment rows; {len(counts):,} distinct vendor strings.")
    print(f"Matched {matched:,} rows ({100*matched/total_rows:.1f}%) to seed nonprofits.")
    print()
    print("Top 20 vendors by row count (any vendor, matched or not):")
    for v, n in counts.most_common(20):
        print(f"  {n:6d}  ${totals[v]:14,.2f}  {v}")
    print()
    print("Seed-matched canonicals (rows + summed amounts in window):")
    for canon, n in matched_counts.most_common():
        print(f"  {n:6d}  ${matched_totals[canon]:14,.2f}  {canon}")


def main(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Denver Checkbook scan / probe")
    p.add_argument("--columns", action="store_true", help="Print dataset columns and exit")
    p.add_argument("--sample", action="store_true", help="Print a sample row dump")
    p.add_argument("--vendor-counts", action="store_true", help="Top vendors + seed match summary")
    p.add_argument("--rows", type=int, default=500, help="Row budget for scans")
    args = p.parse_args(list(argv) if argv is not None else None)

    client = SocrataClient()
    print(f"Endpoint: {client.dataset.resource_url}")
    print(f"App token in use: {'yes' if client.app_token else 'no (anonymous)'}\n")

    if args.columns:
        cmd_columns(client)
        return 0
    if args.sample:
        cmd_sample(client, args.rows)
        return 0
    if args.vendor_counts:
        cmd_vendor_counts(client, args.rows)
        return 0

    # Default: print columns + small sample
    cmd_columns(client)
    print()
    cmd_sample(client, min(args.rows, 5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
