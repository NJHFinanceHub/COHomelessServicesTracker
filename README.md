# Denver Homelessness Dollar Tracker

Tracing every taxpayer dollar Denver spends on homelessness — from source (taxes, bond proceeds, federal grants) to city department to nonprofit recipient to reported beneficiaries — with primary-source citations on every number.

This is not a "$X per homeless person" leaderboard. It is a financial flow map plus per-program unit economics, computed only within comparable service categories, with explicit confidence tiers and a public corrections log.

## Status

**Phase 0 — Foundation.** Repo scaffold, schema, methodology v0.1, source inventory, and a Socrata client skeleton for the Denver Open Checkbook.

See [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) for the full brief and [`docs/methodology.md`](./docs/methodology.md) for the cost-per-beneficiary methodology.

## Repo layout

```
/etl     Python ETL — one source folder per upstream dataset
/db      SQLite schema and migrations
/data    Raw / interim / processed data (mostly gitignored)
/web     Next.js 14 frontend
/docs    Methodology, source inventory, data dictionary, changelog
```

## Quick start

```bash
# Initialize SQLite db from schema
make db

# Run ETL (Phase 1+)
make etl

# Compute unit economics
make compute

# Build the static site
make build
```

## Editorial principles

- Every numeric claim links to a primary source. No exceptions.
- Show the math: every computed metric expands to show inputs and allocation method.
- Show the gaps: data-quality dashboard with freshness and missing-data percentages.
- No aggregation across service-category tiers. Bed-nights are not housed-households.
- Public corrections log — citizens submit corrections via GitHub issues.

## License

Code: MIT. Data and citations: public-domain primary sources, attributed inline.
