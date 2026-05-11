"""
Phase 6 (early): emit JSON the frontend can render.

NOT yet computing per-unit costs — that needs outcome data we don't have
ingested yet. This step does the safe-to-publish things:

  - Per-recipient totals (count, sum, first/last payment date)
  - Per-recipient annual breakdown
  - Per-recipient top departments and top funding sources

All emitted as static JSON in data/processed/ for the Next.js frontend.

When outcome data lands (Phase 5), per-unit-cost computation slots in
here, GATED by the tier rules in docs/methodology.md. Cross-tier
aggregation must remain impossible.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _per_recipient_summary(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Aggregate per-recipient: total, count, date range, by-year, top departments/funding."""
    base_rows = con.execute(
        """
        SELECT r.id, r.legal_name,
               COUNT(p.id)            AS n_payments,
               COALESCE(SUM(p.amount), 0) AS total_paid,
               MIN(p.payment_date)    AS first_date,
               MAX(p.payment_date)    AS last_date
        FROM recipient r
        LEFT JOIN payment p ON p.recipient_id = r.id
        GROUP BY r.id, r.legal_name
        ORDER BY total_paid DESC, r.legal_name ASC
        """
    ).fetchall()

    out: list[dict[str, Any]] = []
    for rid, name, n, total, first_date, last_date in base_rows:
        by_year: dict[str, float] = defaultdict(float)
        dept_totals: dict[str, float] = defaultdict(float)
        fund_totals: dict[str, float] = defaultdict(float)
        for payment_date, amount, dept_name, fund_code in con.execute(
            """
            SELECT p.payment_date, p.amount, a.name, p.fund_code
            FROM payment p
            JOIN agency a ON a.id = p.agency_id
            WHERE p.recipient_id = ?
            """,
            (rid,),
        ):
            year = (payment_date or "")[:4] or "unknown"
            by_year[year] += float(amount or 0)
            if dept_name:
                dept_totals[dept_name] += float(amount or 0)
            if fund_code:
                fund_totals[fund_code] += float(amount or 0)

        top_depts = sorted(dept_totals.items(), key=lambda x: -x[1])[:3]
        top_funds = sorted(fund_totals.items(), key=lambda x: -x[1])[:3]

        out.append(
            {
                "id": rid,
                "legal_name": name,
                "n_payments": int(n or 0),
                "total_paid": round(float(total or 0), 2),
                "first_payment_date": first_date,
                "last_payment_date": last_date,
                "by_year": {y: round(v, 2) for y, v in sorted(by_year.items())},
                "top_departments": [
                    {"name": d, "amount": round(v, 2)} for d, v in top_depts
                ],
                "top_funding_sources": [
                    {"name": f, "amount": round(v, 2)} for f, v in top_funds
                ],
            }
        )
    return out


def _meta(con: sqlite3.Connection) -> dict[str, Any]:
    last_fetch = con.execute(
        """
        SELECT MAX(fetched_at) FROM source_fetch
        WHERE source_name = 'denver_checkbook'
        """
    ).fetchone()
    n_recipients = con.execute("SELECT COUNT(*) FROM recipient").fetchone()[0]
    n_payments = con.execute("SELECT COUNT(*) FROM payment").fetchone()[0]
    return {
        "generated_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "last_checkbook_fetch_at": last_fetch[0] if last_fetch else None,
        "n_recipients": int(n_recipients),
        "n_payments": int(n_payments),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compute and emit frontend JSON")
    p.add_argument("--db", required=True)
    p.add_argument("--out", required=True, help="Output directory for JSON files")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"ERROR: db not found at {db_path}", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(db_path))
    try:
        meta = _meta(con)
        recipients = _per_recipient_summary(con)
    finally:
        con.close()

    payload = {"meta": meta, "recipients": recipients}
    out_path = out_dir / "recipients.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        f"Wrote {out_path}: {meta['n_recipients']} recipients, "
        f"{meta['n_payments']} payments."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
