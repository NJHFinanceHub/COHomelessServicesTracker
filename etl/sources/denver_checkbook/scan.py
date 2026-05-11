"""
Phase 0 / pre-Phase-1 scan tool.

Probes the live Denver Checkbook dataset and writes its findings to disk so
that Phase 1 can rely on a verified column map instead of guessing. Modes:

    --columns          Discover real column names and write
                       data/raw/checkbook_columns.json
    --date-range       Min/max paymentdate + per-year counts; write
                       data/raw/checkbook_date_range.json
    --sample           Dump the first N rows as JSON
    --vendor-counts    Top vendors + seed match summary
    --new-candidates   Curator-loop output: top unmatched vendors → CSV in
                       data/interim/ for human review before seed expansion

Usage examples:
    python -m etl.sources.denver_checkbook.scan --columns
    python -m etl.sources.denver_checkbook.scan --date-range
    python -m etl.sources.denver_checkbook.scan --vendor-counts --rows 5000
    python -m etl.sources.denver_checkbook.scan --new-candidates --rows 20000

Phase 1 (`run.py`) refuses to ingest until --columns has been run and its
output is committed to the repo. This guarantees we never bind to a guessed
field name in production.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .client import SocrataClient
from .entity_resolution import match_vendor


# Heuristic candidates for the dataset's key fields. We discover the real one
# at runtime via the metadata endpoint and pick the first match. Public
# documentation suggests the vendor column is "Payee", so we list payee
# variants first.
VENDOR_FIELD_CANDIDATES = [
    "payee",
    "payee_name",
    "vendor_name",
    "vendor",
    "supplier_name",
    "company_name",
]
AMOUNT_FIELD_CANDIDATES = [
    "payment_amount",
    "amount",
    "check_amount",
    "expenditure_amount",
    "warrant_amount",
    "paid_amount",
]
DATE_FIELD_CANDIDATES = [
    "payment_date",
    "check_date",
    "warrant_date",
    "transaction_date",
    "post_date",
    "date",
    "fiscal_year",
]

# Where we persist artifacts. Paths are relative to the repo root.
COLUMNS_OUT = Path("data/raw/checkbook_columns.json")
DATE_RANGE_OUT = Path("data/raw/checkbook_date_range.json")
CATALOG_OUT = Path("data/raw/socrata_catalog_denver_checkbook.json")
NEW_CANDIDATES_DIR = Path("data/interim")


def discover_field(columns: List[Dict[str, str]], candidates: List[str]) -> Optional[str]:
    """Pick the first candidate present as an exact `fieldName`, with a
    case-insensitive substring fallback. Returns None if nothing matches."""
    field_names = {c["fieldName"]: c for c in columns}
    for cand in candidates:
        if cand in field_names:
            return cand
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
        last_iso = dt.datetime.fromtimestamp(last, tz=dt.timezone.utc).isoformat()
        print(f"rowsUpdatedAt: {last} ({last_iso})")

    vendor_field = discover_field(cols, VENDOR_FIELD_CANDIDATES)
    amount_field = discover_field(cols, AMOUNT_FIELD_CANDIDATES)
    date_field = discover_field(cols, DATE_FIELD_CANDIDATES)
    print(f"Resolved fields: vendor={vendor_field}  amount={amount_field}  date={date_field}")

    # Persist for Phase 1 to consume.
    COLUMNS_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "endpoint": client.dataset.resource_url,
        "dataset_id": client.dataset.dataset_id,
        "fetched_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "rows_updated_at": last,
        "columns": cols,
        "resolved": {
            "vendor_field": vendor_field,
            "amount_field": amount_field,
            "date_field": date_field,
        },
    }
    COLUMNS_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"\nWrote {COLUMNS_OUT}")


def cmd_sample(client: SocrataClient, rows: int) -> None:
    print(f"Fetching first {rows} rows...")
    rows_out = list(client.query(limit=min(rows, 1000), max_rows=rows))
    print(f"Got {len(rows_out)} rows. First row keys:")
    if rows_out:
        print(json.dumps(sorted(rows_out[0].keys()), indent=2))
        print("\nFirst 3 rows (full):")
        for r in rows_out[:3]:
            print(json.dumps(r, indent=2, default=str))


def _resolve_fields(client: SocrataClient) -> tuple[str, Optional[str], Optional[str], List[Dict[str, str]]]:
    cols = client.columns()
    vendor_field = discover_field(cols, VENDOR_FIELD_CANDIDATES)
    amount_field = discover_field(cols, AMOUNT_FIELD_CANDIDATES)
    date_field = discover_field(cols, DATE_FIELD_CANDIDATES)
    if not vendor_field:
        print("ERROR: could not find a vendor-name column. Re-run with --columns to inspect.", file=sys.stderr)
        sys.exit(2)
    print(f"Discovered fields: vendor={vendor_field}  amount={amount_field}  date={date_field}")
    return vendor_field, amount_field, date_field, cols


def _stream_window(client: SocrataClient, *, vendor_field: str, amount_field: Optional[str],
                   date_field: Optional[str], rows: int) -> tuple[Counter, Dict[str, float], int, Counter, Dict[str, float], List[tuple[str, str]]]:
    """Stream `rows` records and return per-vendor stats plus per-row matches."""
    order_clause = f"{date_field} DESC" if date_field else None
    counts: Counter[str] = Counter()
    totals: Dict[str, float] = defaultdict(float)
    matched_counts: Counter[str] = Counter()
    matched_totals: Dict[str, float] = defaultdict(float)
    matched_rows = 0
    matches: List[tuple[str, str]] = []  # (vendor_string, canonical) for matched rows

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
            matched_rows += 1
            matched_counts[m.seed.canonical] += 1
            matched_totals[m.seed.canonical] += amt
            matches.append((v, m.seed.canonical))
        else:
            matches.append((v, ""))
    return counts, totals, matched_rows, matched_counts, matched_totals, matches


def cmd_vendor_counts(client: SocrataClient, rows: int) -> None:
    vendor_field, amount_field, date_field, _ = _resolve_fields(client)
    print(f"Streaming {rows} rows ordered by {date_field or ':id'} desc...")
    counts, totals, matched_rows, matched_counts, matched_totals, _ = _stream_window(
        client, vendor_field=vendor_field, amount_field=amount_field,
        date_field=date_field, rows=rows,
    )
    total_rows = sum(counts.values())
    if total_rows == 0:
        print("No rows scanned.")
        return
    print()
    print(f"Scanned {total_rows:,} payment rows; {len(counts):,} distinct vendor strings.")
    print(f"Matched {matched_rows:,} rows ({100*matched_rows/total_rows:.1f}%) to seed nonprofits.")
    print()
    print("Top 20 vendors by row count (any vendor, matched or not):")
    for v, n in counts.most_common(20):
        print(f"  {n:6d}  ${totals[v]:14,.2f}  {v}")
    print()
    print("Seed-matched canonicals (rows + summed amounts in window):")
    for canon, n in matched_counts.most_common():
        print(f"  {n:6d}  ${matched_totals[canon]:14,.2f}  {canon}")


def cmd_date_range(client: SocrataClient) -> None:
    """Query dataset-wide min/max paymentdate plus per-year counts and totals.

    This answers two questions: (1) what is the dataset's actual date span,
    and (2) what does the year-by-year distribution look like — useful for
    diagnosing 'why is only year X in our DB?' issues.

    Uses SoQL aggregates so we never page through real rows.
    """
    cols = client.columns()
    date_field = discover_field(cols, DATE_FIELD_CANDIDATES)
    amount_field = discover_field(cols, AMOUNT_FIELD_CANDIDATES)
    if not date_field:
        print("ERROR: no date column found.", file=sys.stderr)
        sys.exit(2)
    print(f"Querying min/max {date_field} and per-year aggregate...")

    # 1) overall min/max + total row count
    overall = list(
        client.query(
            select=(
                f"min({date_field}) AS min_date, "
                f"max({date_field}) AS max_date, "
                f"count(*) AS n_total"
                + (f", sum({amount_field}) AS sum_total" if amount_field else "")
            ),
            limit=1,
            max_rows=1,
        )
    )
    overall_row = overall[0] if overall else {}
    min_date = overall_row.get("min_date")
    max_date = overall_row.get("max_date")
    n_total = int(overall_row.get("n_total") or 0)
    sum_total = float(overall_row.get("sum_total") or 0) if amount_field else None

    # 2) per-year counts. Socrata's date_extract_y on calendar_date returns year as int.
    # GROUP BY is required by SoQL when mixing aggregate and non-aggregate select cols.
    year_expr = f"date_extract_y({date_field})"
    per_year_rows = list(
        client.query(
            select=(
                f"{year_expr} AS year, count(*) AS n"
                + (f", sum({amount_field}) AS amount" if amount_field else "")
            ),
            where=f"{date_field} IS NOT NULL",
            group=year_expr,
            order="year ASC",
            limit=200,
            max_rows=200,
        )
    )
    per_year = [
        {
            "year": str(int(float(r["year"]))) if r.get("year") is not None else "unknown",
            "n_payments": int(r.get("n") or 0),
            "total": float(r.get("amount") or 0) if amount_field else None,
        }
        for r in per_year_rows
    ]

    payload = {
        "endpoint": client.dataset.resource_url,
        "dataset_id": client.dataset.dataset_id,
        "fetched_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "min_date": min_date,
        "max_date": max_date,
        "n_total_rows": n_total,
        "sum_total": sum_total,
        "per_year": per_year,
    }
    DATE_RANGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATE_RANGE_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {DATE_RANGE_OUT}")
    print(f"min_date={min_date}  max_date={max_date}  n_total={n_total:,}")
    print("Per-year counts:")
    for r in per_year:
        amt = f"  ${r['total']:14,.0f}" if r.get("total") is not None else ""
        print(f"  {r['year']}: {r['n_payments']:7,d}{amt}")


def cmd_catalog_search() -> None:
    """Search Socrata's Discovery API for Denver-checkbook-related datasets.

    The known production dataset (wnau-xrqi) is current-year-only; finding
    sibling/archive datasets is the way to get prior-year data. The Discovery
    API at api.us.socrata.com lists all public datasets across all domains
    and supports search by name/keywords.
    """
    import urllib.parse
    import urllib.request

    queries = [
        ("denver+checkbook", "domains=data.colorado.gov"),
        ("denver+checkbook", ""),
        ("denver+payment", "domains=data.colorado.gov"),
        ("city+denver+expenditure", "domains=data.colorado.gov"),
    ]
    aggregated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for q, extra in queries:
        url = f"https://api.us.socrata.com/api/catalog/v1?q={q}&{extra}&limit=50" if extra else f"https://api.us.socrata.com/api/catalog/v1?q={q}&limit=50"
        print(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "denver-tracker/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  failed: {e}")
            continue
        for hit in data.get("results", []):
            res = hit.get("resource", {})
            rid = res.get("id")
            if not rid or rid in seen_ids:
                continue
            seen_ids.add(rid)
            aggregated.append(
                {
                    "id": rid,
                    "name": res.get("name"),
                    "description": (res.get("description") or "").strip()[:400],
                    "domain": hit.get("metadata", {}).get("domain"),
                    "type": res.get("type"),
                    "updatedAt": res.get("updatedAt"),
                    "createdAt": res.get("createdAt"),
                    "columns_field_name": res.get("columns_field_name", []),
                    "row_count": res.get("rows_updated_at"),
                    "permalink": hit.get("permalink"),
                }
            )

    # Filter to anything that looks payment/expenditure/checkbook-related.
    def relevant(d: dict) -> bool:
        text = " ".join(
            str(d.get(k, "")).lower() for k in ("name", "description")
        )
        return any(
            kw in text
            for kw in (
                "checkbook",
                "payment",
                "expenditure",
                "spending",
                "vendor",
                "payee",
            )
        )

    filtered = [d for d in aggregated if relevant(d)]
    filtered.sort(key=lambda d: (d.get("domain") != "data.colorado.gov", d.get("name") or ""))

    payload = {
        "fetched_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "queries": [{"q": q, "extra": extra} for q, extra in queries],
        "n_hits_total": len(aggregated),
        "n_hits_filtered": len(filtered),
        "hits": filtered,
    }
    CATALOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {CATALOG_OUT} ({len(filtered)} relevant datasets)")
    for d in filtered[:30]:
        print(f"  {d['id']:14s}  {d.get('domain','?'):30s}  {d.get('name','')}")


def cmd_new_candidates(client: SocrataClient, rows: int, top: int = 200) -> None:
    """Write the top unmatched vendors to a CSV for human review.

    The Phase 1 ingest only writes payments whose vendor_name matched a seed.
    That's the safe default — but it means we silently miss new recipients
    until the seed list catches up. This command is the curator-loop output:
    review the CSV, add real homelessness recipients to vendor_seeds.SEEDS,
    re-run, re-review until the unmatched tail is clearly non-homelessness.
    """
    vendor_field, amount_field, date_field, _ = _resolve_fields(client)
    print(f"Streaming {rows} rows ordered by {date_field or ':id'} desc...")
    counts, totals, matched_rows, _, _, _ = _stream_window(
        client, vendor_field=vendor_field, amount_field=amount_field,
        date_field=date_field, rows=rows,
    )
    unmatched = [(v, counts[v], totals[v]) for v in counts if not match_vendor(v)]
    unmatched.sort(key=lambda x: (-x[2], -x[1], x[0]))  # by total desc, then count
    unmatched = unmatched[:top]

    NEW_CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = NEW_CANDIDATES_DIR / f"new_candidates_{stamp}.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["vendor_string_raw", "row_count", "total_paid_in_window"])
        for v, n, t in unmatched:
            w.writerow([v, n, f"{t:.2f}"])
    print(f"Wrote {out} ({len(unmatched)} unmatched candidates).")


def main(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Denver Checkbook scan / probe")
    p.add_argument("--columns", action="store_true", help="Discover and persist column map")
    p.add_argument("--date-range", action="store_true",
                   help="Persist dataset min/max paymentdate and per-year counts")
    p.add_argument("--catalog-search", action="store_true",
                   help="Search Socrata's Discovery API for sibling Denver checkbook datasets")
    p.add_argument("--sample", action="store_true", help="Print a sample row dump")
    p.add_argument("--vendor-counts", action="store_true", help="Top vendors + seed match summary")
    p.add_argument("--new-candidates", action="store_true",
                   help="Write top unmatched vendors to data/interim/ for curator review")
    p.add_argument("--rows", type=int, default=500, help="Row budget for scans")
    p.add_argument("--top", type=int, default=200, help="How many unmatched candidates to write (with --new-candidates)")
    args = p.parse_args(list(argv) if argv is not None else None)

    client = SocrataClient()
    print(f"Endpoint: {client.dataset.resource_url}")
    print(f"App token in use: {'yes' if client.app_token else 'no (anonymous)'}\n")

    if args.columns:
        cmd_columns(client)
        return 0
    if args.date_range:
        cmd_date_range(client)
        return 0
    if args.catalog_search:
        cmd_catalog_search()
        return 0
    if args.sample:
        cmd_sample(client, args.rows)
        return 0
    if args.vendor_counts:
        cmd_vendor_counts(client, args.rows)
        return 0
    if args.new_candidates:
        cmd_new_candidates(client, args.rows, top=args.top)
        return 0

    # Default: print columns + small sample
    cmd_columns(client)
    print()
    cmd_sample(client, min(args.rows, 5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
