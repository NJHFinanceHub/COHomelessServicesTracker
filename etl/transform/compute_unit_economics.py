"""
Phase 6 (early): emit JSON the frontend can render.

NOT yet computing per-unit costs — that needs outcome data we don't have
ingested yet. This step computes safe-to-publish financial aggregates.

Output: a single `data/processed/recipients.json` containing:
  - meta            high-level numbers, timestamps, seed-match stats
  - overview        homepage summary (totals, date range, top facts)
  - by_year         year-by-year aggregate spend
  - by_department   city department breakdown
  - by_funding      funding-source breakdown
  - recipients      per-recipient detail with full breakdowns + recent payments
  - seeds           per-seed match status (matched/unmatched + curator notes)

Per-unit costs (cost-per-bed-night, cost-per-PSH-month, etc.) are gated on
the tier rules in docs/methodology.md and require outcome data — punted to
Phase 5.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from etl.sources.denver_checkbook.vendor_seeds import SEEDS


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    s = SLUG_RE.sub("-", name.lower()).strip("-")
    return s or "unknown"


def _per_recipient_summary(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Rich per-recipient detail. Each row includes:
       - top-line totals (count, sum, date range)
       - full year / department / funding-source / expense-category breakdowns
       - a recent-payments sample (most-recent 50, for detail-page rendering)
    """
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
        by_year_count: dict[str, int] = defaultdict(int)
        dept_totals: dict[str, float] = defaultdict(float)
        fund_totals: dict[str, float] = defaultdict(float)
        cat_totals: dict[str, float] = defaultdict(float)

        for payment_date, amount, dept_name, fund_code, obj_code in con.execute(
            """
            SELECT p.payment_date, p.amount, a.name, p.fund_code, p.object_code
            FROM payment p
            JOIN agency a ON a.id = p.agency_id
            WHERE p.recipient_id = ?
            """,
            (rid,),
        ):
            year = (payment_date or "")[:4] or "unknown"
            amt = float(amount or 0)
            by_year[year] += amt
            by_year_count[year] += 1
            if dept_name:
                dept_totals[dept_name] += amt
            if fund_code:
                fund_totals[fund_code] += amt
            if obj_code:
                cat_totals[obj_code] += amt

        recent = [
            {
                "date": row[0],
                "amount": round(float(row[1] or 0), 2),
                "department": row[2],
                "funding_source": row[3],
                "expense_category": row[4],
                "description": row[5],
            }
            for row in con.execute(
                """
                SELECT p.payment_date, p.amount, a.name, p.fund_code,
                       p.object_code, p.description
                FROM payment p
                JOIN agency a ON a.id = p.agency_id
                WHERE p.recipient_id = ?
                ORDER BY p.payment_date DESC, p.id DESC
                LIMIT 50
                """,
                (rid,),
            )
        ]

        out.append(
            {
                "id": rid,
                "legal_name": name,
                "slug": slugify(name),
                "n_payments": int(n or 0),
                "total_paid": round(float(total or 0), 2),
                "first_payment_date": first_date,
                "last_payment_date": last_date,
                "years_active": sorted(by_year.keys()),
                "by_year": [
                    {"year": y, "amount": round(by_year[y], 2),
                     "n_payments": by_year_count[y]}
                    for y in sorted(by_year.keys())
                ],
                "by_department": [
                    {"name": d, "amount": round(v, 2)}
                    for d, v in sorted(dept_totals.items(), key=lambda x: -x[1])
                ],
                "by_funding_source": [
                    {"name": f, "amount": round(v, 2)}
                    for f, v in sorted(fund_totals.items(), key=lambda x: -x[1])
                ],
                "by_expense_category": [
                    {"name": c, "amount": round(v, 2)}
                    for c, v in sorted(cat_totals.items(), key=lambda x: -x[1])
                ],
                "recent_payments": recent,
            }
        )
    return out


def _aggregate_by_year(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT substr(p.payment_date, 1, 4) AS year,
               COUNT(p.id) AS n_payments,
               COALESCE(SUM(p.amount), 0) AS total,
               COUNT(DISTINCT p.recipient_id) AS n_recipients
        FROM payment p
        WHERE p.payment_date IS NOT NULL
        GROUP BY year
        ORDER BY year ASC
        """
    ).fetchall()
    return [
        {
            "year": row[0],
            "n_payments": int(row[1]),
            "total": round(float(row[2]), 2),
            "n_recipients": int(row[3]),
        }
        for row in rows
        if row[0]
    ]


def _aggregate_by_month(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Per-month aggregate. Useful when only one year of data is available —
    surfaces seasonality and any obvious one-time payouts within the year."""
    rows = con.execute(
        """
        SELECT substr(p.payment_date, 1, 7) AS year_month,
               COUNT(p.id) AS n_payments,
               COALESCE(SUM(p.amount), 0) AS total,
               COUNT(DISTINCT p.recipient_id) AS n_recipients
        FROM payment p
        WHERE p.payment_date IS NOT NULL
        GROUP BY year_month
        ORDER BY year_month ASC
        """
    ).fetchall()
    return [
        {
            "year_month": row[0],
            "n_payments": int(row[1]),
            "total": round(float(row[2]), 2),
            "n_recipients": int(row[3]),
        }
        for row in rows
        if row[0]
    ]


def _aggregate_by_department(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT a.name,
               COUNT(p.id) AS n_payments,
               COALESCE(SUM(p.amount), 0) AS total,
               COUNT(DISTINCT p.recipient_id) AS n_recipients
        FROM payment p
        JOIN agency a ON a.id = p.agency_id
        GROUP BY a.name
        ORDER BY total DESC
        """
    ).fetchall()
    out = []
    for name, n_payments, total, n_recipients in rows:
        # Top 5 recipients for this department, for drill-down rendering.
        top_r = [
            {"name": rname, "amount": round(float(amt), 2)}
            for rname, amt in con.execute(
                """
                SELECT r.legal_name, SUM(p.amount) AS amt
                FROM payment p
                JOIN recipient r ON r.id = p.recipient_id
                WHERE p.agency_id = (SELECT id FROM agency WHERE name = ?)
                GROUP BY r.legal_name
                ORDER BY amt DESC
                LIMIT 5
                """,
                (name,),
            )
        ]
        out.append(
            {
                "name": name,
                "slug": slugify(name),
                "n_payments": int(n_payments),
                "total": round(float(total), 2),
                "n_recipients": int(n_recipients),
                "top_recipients": top_r,
            }
        )
    return out


def _aggregate_by_funding(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT p.fund_code AS name,
               COUNT(p.id) AS n_payments,
               COALESCE(SUM(p.amount), 0) AS total,
               COUNT(DISTINCT p.recipient_id) AS n_recipients
        FROM payment p
        WHERE p.fund_code IS NOT NULL AND p.fund_code != ''
        GROUP BY p.fund_code
        ORDER BY total DESC
        """
    ).fetchall()
    return [
        {
            "name": row[0],
            "slug": slugify(row[0]),
            "n_payments": int(row[1]),
            "total": round(float(row[2]), 2),
            "n_recipients": int(row[3]),
        }
        for row in rows
    ]


def _overview(meta: dict[str, Any], recipients: list[dict[str, Any]],
              by_year: list[dict[str, Any]], by_dept: list[dict[str, Any]],
              by_funding: list[dict[str, Any]]) -> dict[str, Any]:
    total_paid = sum(r["total_paid"] for r in recipients)
    matched = [r for r in recipients if r["n_payments"] > 0]
    first = min((r["first_payment_date"] for r in matched if r["first_payment_date"]), default=None)
    last = max((r["last_payment_date"] for r in matched if r["last_payment_date"]), default=None)
    years_active = sorted({y["year"] for y in by_year})
    return {
        "total_paid": round(total_paid, 2),
        "n_payments": int(meta.get("n_payments", 0)),
        "n_recipients_matched": len(matched),
        "n_seeds_total": meta.get("n_seeds"),
        "n_seeds_matched": meta.get("n_seeds_matched"),
        "n_departments": len(by_dept),
        "n_funding_sources": len(by_funding),
        "first_payment_date": first,
        "last_payment_date": last,
        "n_years": len(years_active),
        "years_active": years_active,
        "top_recipient": (
            {"name": matched[0]["legal_name"], "amount": matched[0]["total_paid"]}
            if matched else None
        ),
        "top_department": (
            {"name": by_dept[0]["name"], "amount": by_dept[0]["total"]}
            if by_dept else None
        ),
        "top_funding_source": (
            {"name": by_funding[0]["name"], "amount": by_funding[0]["total"]}
            if by_funding else None
        ),
    }


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


def _seeds_summary(recipients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-seed: did this seed match anything? With notes for curator review."""
    by_canonical = {r["legal_name"]: r for r in recipients}
    out = []
    for s in SEEDS:
        r = by_canonical.get(s.canonical)
        out.append(
            {
                "canonical": s.canonical,
                "distinctive": s.distinctive,
                "notes": s.notes,
                "matched": bool(r and r.get("n_payments", 0) > 0),
                "n_payments": int(r["n_payments"]) if r else 0,
                "total_paid": float(r["total_paid"]) if r else 0.0,
            }
        )
    return out


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
        by_year = _aggregate_by_year(con)
        by_month = _aggregate_by_month(con)
        by_dept = _aggregate_by_department(con)
        by_funding = _aggregate_by_funding(con)
    finally:
        con.close()

    seeds = _seeds_summary(recipients)
    meta["n_seeds"] = len(seeds)
    meta["n_seeds_matched"] = sum(1 for s in seeds if s["matched"])

    overview = _overview(meta, recipients, by_year, by_dept, by_funding)

    payload = {
        "meta": meta,
        "overview": overview,
        "by_year": by_year,
        "by_month": by_month,
        "by_department": by_dept,
        "by_funding": by_funding,
        "recipients": recipients,
        "seeds": seeds,
    }
    out_path = out_dir / "recipients.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        f"Wrote {out_path}: {meta['n_recipients']} recipients, "
        f"{meta['n_payments']} payments, seeds matched {meta['n_seeds_matched']}/{meta['n_seeds']}, "
        f"{len(by_year)} years, {len(by_dept)} depts, {len(by_funding)} funding sources."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
