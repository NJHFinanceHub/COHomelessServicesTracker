# Data dictionary

Field-level reference for the v1 SQLite schema (`db/schema.sql`). Describes only fields whose meaning is non-obvious from the column name.

## `funding_source`

- **`type`** — one of `federal`, `state`, `local-tax`, `bond`, `philanthropic`, `fee`, `other`. Determines top-level color in the Sankey.
- **`legal_authority`** — the ballot measure, ordinance, or statute that created the source (e.g., "Ballot 2B 2020" for the Homelessness Resolution Fund).

## `appropriation`

- **`extraction_confidence`** — `manual` (a human entered or verified the row), `auto-high` / `auto-medium` / `auto-low` (PDF or scrape extracted with declining confidence).
- **`source_doc_page`** — page number in the cited budget document. Required for any `auto-*` confidence.

## `recipient`

- **`dba_names`** — JSON array of alternate names. Populated by the entity-resolution step; used to match Checkbook vendor strings.
- **`propublica_id`** — the ID used by the ProPublica Nonprofit Explorer API for this organization. Used to fetch 990 financials.

## `service_category`

- **`unit_of_service`** — the only unit per-unit math may use for this category. Free-text but constrained by the editorial set in `docs/methodology.md`.

## `payment`

- **`source_dataset`** — namespace plus dataset id, e.g. `denver_checkbook:wnau-xrqi`.
- **`source_row_id`** — the upstream row identifier (Socrata `:id`, Legistar matter id, etc.). Combined with `source_dataset` this is the idempotency key.
- **`fund_code` / `object_code`** — Denver budget account codes; preserved verbatim for auditability.

## `outcome_report`

- **`reporting_standard`** — declares the methodology behind the number. Used to assign confidence tier:
  - `HMIS`, `HUD-CAPER` → eligible for Tier 1
  - `HOST-quarterly` → typically Tier 2
  - `mayors-dashboard`, `self-reported` → Tier 3
- **`data_quality_score`** — 0–100, set by the loader based on completeness checks.

## `cost_allocation`

- **`allocation_method`** — see methodology document. The `CHECK` constraint at the row level enforces exactly one of `payment_id` / `appropriation_id` is set, never both.
- **`allocator_notes`** — free-text justification. Required for `pro-rata` and `estimated`.

## `source_fetch`

Provenance log. Every fetch (HTTP or otherwise) writes a row here so we can reproduce any number on the site from the original bytes.
