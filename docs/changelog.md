# Changelog

Material changes to data, methodology, or schema. Date format: ISO-8601.

## 2026-04-29 — Phase 0 scaffold

- Repo initialized on branch `claude/denver-homelessness-tracker-jZDcn`.
- Schema v1 written (`db/schema.sql`).
- Methodology v0.1 published (`docs/methodology.md`).
- Source inventory created (`docs/source-inventory.md`); all 15 sources marked "not yet ingested" except Denver Checkbook which is "scaffolded".
- Next.js 14 placeholder site with methodology page only.
- Socrata client skeleton in `etl/sources/denver_checkbook/` — not yet writing to DB.
- Entity-resolution heuristic implemented and unit-tested (6/6 passing): whole-token matching against curated seed list of 30 Denver-area homelessness nonprofits with distinctive substrings + alias lists.
- Live Socrata probe is the next outstanding action — must be run from an environment with internet egress (the build environment used for Phase 0 had none). Run: `python -m etl.sources.denver_checkbook.scan --columns` then `--vendor-counts --rows 5000`.

## 2026-05-11 — Phase 1 ingest wired

- Real Denver Open Checkbook ingest in `etl/sources/denver_checkbook/run.py`:
  - Per-seed Socrata query (server-side substring filter on the distinctive phrase, capped by `--since` / `--max-rows-per-seed`)
  - Client-side re-match against `entity_resolution.match_vendor` so server-side LIKE can't cause cross-talk
  - Idempotent inserts keyed on `(source_dataset, source_row_id)` where `source_row_id` is the Socrata `:id`
  - $0 voids and adjustments excluded; full audit-trail switch can be added later
- `etl/transform/compute_unit_economics.py` now real (not a stub): emits `data/processed/recipients.json` with per-recipient totals, annual breakdown, and top departments / funding sources. Per-unit costs deferred until outcome data lands (Phase 5).
- New `web/app/recipients/page.tsx` reads that JSON and renders the recipients table. Linked from the home page.
- New tests: `etl/tests/test_db_upserts.py` (8 cases) and `etl/tests/test_ingest_loop.py` (5 cases) using in-memory SQLite and a fake Socrata client. Total tests now 24, all passing.

## 2026-04-29 — Phase 0.1 deviations applied

- Reordered `VENDOR_FIELD_CANDIDATES` to put `payee` first (public dataset hint).
- `scan.py --columns` now persists a verified column map to `data/raw/checkbook_columns.json` (whitelisted in `.gitignore`).
- `scan.py --new-candidates` writes a "top unmatched vendors" CSV to `data/interim/` for the curator review loop before any DB ingest.
- `run.py` (Phase 1) now refuses to start without a committed column-map artifact whose `vendor_field` / `amount_field` / `date_field` are all resolved.
- Added `etl/tests/test_discover_field.py` (5 cases). Total tests: 11 passing.
