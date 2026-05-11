# Source inventory

Every primary source the site relies on, with current ingest status. Status legend:

- **not yet ingested** — known and planned, no code yet
- **scaffolded** — extractor exists but not run against live data
- **piloted** — successfully fetched a small sample
- **live** — running on schedule, populating production data
- **stale** — ran successfully once but not on current cadence
- **broken** — extractor exists but currently fails

| # | Source | Access | Cadence | Phase | Status |
|---|---|---|---|---|---|
| 1 | Denver Open Checkbook | Socrata SODA 2.0 — `data.colorado.gov/Business/City-of-Denver-Checkbook/wnau-xrqi` | Daily | 1 | piloted; column probe verified, ingest implemented, awaiting first nightly run |
| 2 | Denver Open Data Catalog (contracts, P-card, vendor master) | `denvergov.org/opendata` | Varies | 3 | not yet ingested |
| 3 | HOST Annual Action Plans | `denvergov.org` HOST plans-and-reports page (PDF) | Annual | 2 | not yet ingested |
| 4 | HOST quarterly performance reports | Same page (PDF) | Quarterly | 5 | not yet ingested |
| 5 | All In Mile High dashboard | Mayor's office site (HTML) | Live | 5 | not yet ingested |
| 6 | MDHI dashboards (PIT, State of Homelessness) | `mdhi.org/data` (Tableau Public) | Annual + ad hoc | 5 | not yet ingested |
| 7 | HUD HDX (PIT/HIC) | `hudexchange.info` (CSV) | Annual | 5 | not yet ingested |
| 8 | HUD CoC awards | `hud.gov/program_offices` (XLS) | Annual | 5 | not yet ingested |
| 9 | IRS 990s | ProPublica Nonprofit Explorer API | Annual | 4 | not yet ingested |
| 10 | Denver Auditor reports | `denvergov.org/auditor` (PDF) | Ongoing | 8 | not yet ingested |
| 11 | Colorado SoS nonprofit registry | `sos.state.co.us` | Ongoing | 4 | not yet ingested |
| 12 | SAM.gov federal grants | `sam.gov` | Ongoing | 5 | not yet ingested |
| 13 | Denver City Council legislative records (Legistar) | `denver.legistar.com` API | Ongoing | 3 | not yet ingested |
| 14 | Denver Budget Books | `denvergov.org/budget` (PDF) | Annual | 2 | not yet ingested |
| 15 | HUD CAPER | `hud.gov` (CSV) | Annual | 5 | not yet ingested |

## Mirroring policy

Every source PDF and HTML snapshot will be mirrored to Cloudflare R2 with a SHA-256 hash and fetch timestamp once Phase 8 ships. City-hosted PDFs disappear regularly; we keep our own copies so citations remain stable.

## Provenance log

All fetches are logged in the `source_fetch` table (see `db/schema.sql`). For Phase 0 the table is empty.

## How to run the Phase 0 column probe

The Phase 1 ingest refuses to run without a committed column-map artifact. To produce it, from a host with network access:

```bash
make db
python -m etl.sources.denver_checkbook.scan --columns
git add data/raw/checkbook_columns.json && git commit -m "data: lock Denver checkbook column map"
```

If the probe writes any of `vendor_field`, `amount_field`, or `date_field` as `null`, inspect the column list in the JSON, add the real field name to the appropriate `*_FIELD_CANDIDATES` list in `etl/sources/denver_checkbook/scan.py`, and re-run.

Then to surface unmatched recipients before extending the seed list:

```bash
python -m etl.sources.denver_checkbook.scan --new-candidates --rows 20000 --top 200
```

This writes a CSV under `data/interim/` listing the highest-spending vendors that the deterministic matcher did not catch. Review the CSV, add genuine homelessness recipients to `etl/sources/denver_checkbook/vendor_seeds.SEEDS`, and re-run until the unmatched tail is clearly out of scope.
