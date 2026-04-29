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

## 2026-04-29 — Phase 0.1 deviations applied

- Reordered `VENDOR_FIELD_CANDIDATES` to put `payee` first (public dataset hint).
- `scan.py --columns` now persists a verified column map to `data/raw/checkbook_columns.json` (whitelisted in `.gitignore`).
- `scan.py --new-candidates` writes a "top unmatched vendors" CSV to `data/interim/` for the curator review loop before any DB ingest.
- `run.py` (Phase 1) now refuses to start without a committed column-map artifact whose `vendor_field` / `amount_field` / `date_field` are all resolved.
- Added `etl/tests/test_discover_field.py` (5 cases). Total tests: 11 passing.
