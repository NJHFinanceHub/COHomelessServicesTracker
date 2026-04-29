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
