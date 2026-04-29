# Denver Homelessness Dollar Tracker — Claude Code Project Plan

A public-facing site that traces every taxpayer dollar Denver spends on homelessness from source (federal/state/local taxes and bond proceeds) → city department → contracted nonprofit → reported beneficiaries, and computes defensible cost-per-beneficiary metrics with full source citation.

This document is the brief. Hand it to Claude Code as `PROJECT_PLAN.md` at the root of a new repo and tell it to start at Phase 0.

-----

## 1. The thesis (and the honest caveat up front)

"Cost per beneficiary" sounds simple but is the single most contested metric in homelessness policy. A shelter bed-night, a permanent supportive housing placement, an eviction-prevention rental assistance check, and an outreach contact are not the same unit and should never be added together. The site's job is not to publish a single number; it's to:

1. **Pin every dollar** to a source, a recipient, a program, and a service category.
1. **Pin every reported outcome** to the same program, with the unit clearly labeled (bed-night, household served, person housed, etc.).
1. **Compute cost-per-unit only within comparable categories**, with confidence indicators based on data completeness.
1. **Show the gaps** — where money flows but outcomes aren't reported, or vice versa.
1. **Cite the source document and line for every number**, so a skeptical reader can verify everything.

If we publish a single "$X per homeless person" headline, we will be wrong and the site will lose credibility in a week. The framing must be a financial flow map plus per-program unit economics, not a leaderboard.

-----

## 2. The funding landscape (as of late 2025/early 2026)

This is what the site needs to model. Use it to design the schema before writing any scrapers.

### Primary city vehicle

- **Department of Housing Stability (HOST)** — Denver's lead agency. ~$229M planned investment in 2025 across affordable housing + homelessness. ~$71.6M general fund request for 2026, with ~$33M in one-time programmatic cuts as ARPA winds down.

### Funding sources flowing into HOST

- **General Fund** (city property/sales tax)
- **Affordable Housing Fund (AHF)** — dedicated property tax + linkage fee, est. 2017
- **Homelessness Resolution Fund (HRF)** — voter-approved 2020 (Ballot 2B), 0.25% sales tax
- **Federal grants** — HUD CoC, ESG, CDBG, HOME, ESG-CV; ~5% of HOST's 2025 budget
- **ARPA / State and Local Fiscal Recovery Funds** — winding down
- **State funds** — Colorado Prop 123 (affordable housing), DOLA grants
- **Other** — DHA bond proceeds, philanthropic match (e.g., Denver Basic Income Project)

### Funding sources flowing OUTSIDE HOST (don't miss these)

- **Denver Health** behavioral health and street outreach contracts
- **DPD/DFD** co-responder program (STAR), encampment response
- **Public Works / Solid Waste** encampment cleanup costs
- **Parks and Rec** facility use for severe-weather shelters
- **DDPHE** harm reduction and outreach
- **Denver Human Services** — TANF-adjacent supports
- **Denver Housing Authority (DHA)** — separate entity, receives city pass-through

### Major nonprofit recipients (partial list to seed the recipient table)

- Colorado Coalition for the Homeless (CCH)
- Volunteers of America (VOA) Colorado
- St. Francis Center
- Catholic Charities of Denver
- Bayaud Enterprises
- Mile High Behavioral Healthcare
- Urban Peak (youth)
- Denver Rescue Mission
- The Salvation Army (Crossroads)
- Brothers Redevelopment
- Mental Health Center of Denver / WellPower
- The Gathering Place
- Mutual Aid Monday partners

### Continuum of Care (regional layer)

- **Metro Denver Homeless Initiative (MDHI)** — HUD-designated CoC; manages HMIS; runs annual PIT count

### Outcomes data sources

- HOST quarterly performance reports
- Mayor Johnston's "All In Mile High" tracking dashboard (the one publishing the 1,950 / 318 / 228 / 81 / 53 / 18 numbers)
- MDHI Point-in-Time count + State of Homelessness Report
- HMIS aggregate reports
- HUD CAPER reports (annual)
- Nonprofit IRS Form 990s (ProPublica Nonprofit Explorer API)
- City audits (Denver Auditor's Office)

-----

## 3. Data sources — concrete URLs and access patterns

| Source | Access | Cadence | Notes |
|---|---|---|---|
| Denver Open Checkbook | denvergov.org/transparency/checkbook + data.colorado.gov/Business/City-of-Denver-Checkbook/wnau-xrqi | Daily | Socrata API (SODA 2.0) — vendor-level payments. **Single most important dataset.** |
| Denver Open Data Catalog | denvergov.org/opendata | Varies | Contracts, P-card, budgets, vendor master |
| HOST Annual Action Plans | denvergov.org HOST plans-and-reports page | Annual | PDF — extract budget tables |
| HOST quarterly reports | Same page | Quarterly | PDF |
| All In Mile High dashboard | Mayor's office site | Live | HTML scrape; capture snapshots over time |
| MDHI dashboards | mdhi.org/data | Annual + ad hoc | Tableau Public embeds — extract underlying data |
| HUD HDX (PIT/HIC) | hudexchange.info | Annual | CSV downloads |
| HUD CoC awards | hud.gov/program_offices | Annual | XLS |
| IRS 990s | propublica.org/nonprofits API | Annual | Free API, JSON |
| Denver Auditor reports | denvergov.org/auditor | Ongoing | PDF |
| Colorado SoS nonprofit registry | sos.state.co.us | Ongoing | Lookup |
| CO Sunshine / SAM.gov | sam.gov | Ongoing | Federal grant cross-reference |
| Denver City Council legislative records | denver.legistar.com | Ongoing | Contract approvals — legistar has an API |
| Denver Budget Books | denvergov.org/budget | Annual | PDF — extract HOST and other agency lines |

A few of these (HOST PDFs, the Mayor's dashboard) will need either targeted PDF parsing or HTML scraping; build extractors as standalone CLI tools so they can be re-run when documents update.

-----

## 4. Data model

Design the schema first. Everything downstream depends on this being right. SQLite for v1 (easy to ship, easy to inspect, easy to migrate to Postgres later).

See `db/schema.sql` for the canonical definition. Highlights:

- `funding_source`, `appropriation`, `agency`, `recipient`, `contract`, `payment`
- `service_category` with explicit `unit_of_service`
- `program` is the operational level where unit economics live
- `outcome_report` carries `reporting_standard` and `data_quality_score`
- `cost_allocation` is the load-bearing wall — it's how a single payment gets mapped to programs with an explicit `allocation_method`
- `org_financials` for 990 data

`cost_allocation` matters most. A single $4M payment to a multi-program nonprofit can't be naively divided by their total beneficiaries — that destroys the whole exercise. The allocation method must be explicit per row, and the UI must show it.

-----

## 5. Cost-per-beneficiary methodology

Define this before computing anything. Publish the methodology page as v1.0 of the site and update it transparently. See `docs/methodology.md`.

### Tiered comparability

- **Tier 1 — directly comparable**: same service category, same reporting standard (HMIS), same period. Show ranges and medians within the tier.
- **Tier 2 — comparable with caveats**: same category, mixed reporting standards. Show with confidence flag.
- **Tier 3 — informational only**: cross-category or self-reported only. Show but never aggregate.

### Per-unit metrics to compute

- Cost per bed-night (Emergency Shelter)
- Cost per household-month sheltered (Transitional/Bridge)
- Cost per household placed in housing (Rapid Rehousing)
- Cost per household-month housed (Permanent Supportive Housing) — separate operating vs capital
- Cost per household stabilized for 12+ months (Eviction Prevention)
- Cost per outreach contact (Street Outreach) — flagged as input metric only
- Admin overhead ratio (from 990s)

### What NOT to do

- Do not compute "cost per homeless person in Denver" by dividing total spending by PIT count. PIT is a one-night snapshot; spending serves a much larger annual cohort with high turnover. This is the single most common misleading framing in homelessness reporting.
- Do not subtract capital from operating without flagging — a building bought once serves people for decades.
- Do not compare a low-acuity day-services org to a high-acuity PSH provider on cost-per-person. The populations are different.
- Do not name-and-shame outliers without first looking at the program mix and acuity.

-----

## 6. Architecture

### Stack

- **Backend**: Python 3.12, SQLite (v1) → Postgres (v2)
- **ETL**: Plain Python scripts in `etl/`, one per source, idempotent, runnable from CLI
- **Orchestration**: `Makefile` for v1; consider Prefect or Dagster only if it actually starts hurting
- **PDF parsing**: `pdfplumber` for tables, `pypdf` for text, `pytesseract` only as fallback
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + Recharts for charts, MapLibre for any geographic views
- **Hosting**: Vercel for the frontend, Cloudflare R2 for static data dumps, GitHub Actions for nightly ETL
- **API**: The frontend reads pre-built JSON files generated by ETL; no live database needed for v1.

### Repo layout

```
/etl
  /sources          # one folder per upstream source
    /denver_checkbook
    /host_action_plans
    /mdhi_pit
    /propublica_990
    /hud_caper
    /legistar_contracts
    /mayors_dashboard
  /transform        # normalization, entity resolution, allocation
  /load             # writes to SQLite + emits JSON for frontend
  /tests
/db
  schema.sql
  /migrations
/data
  /raw              # immutable downloads (gitignored, but indexed)
  /interim          # intermediate parsed files
  /processed        # final JSON consumed by frontend
/web
  /app              # Next.js routes
  /components
  /lib
  /public
/docs
  methodology.md
  data-dictionary.md
  source-inventory.md
  changelog.md
PROJECT_PLAN.md
README.md
Makefile
```

### Key pages

1. **Home** — money flow Sankey: Sources → Agencies → Recipients → Service categories.
1. **Funding sources** — list of every source with year-over-year totals
1. **City agencies** — HOST, DPD, DDPHE, etc.
1. **Recipients** — nonprofit profile pages: contracts, payments, programs, 990s, outcomes, computed unit economics
1. **Programs** — the operational level where unit economics actually live
1. **Compare** — pick programs within a service category and see costs side by side with confidence indicators
1. **Methodology** — long, plain-language explanation of every assumption
1. **Data quality dashboard** — what's missing, what's stale, what's been flagged
1. **Sources** — every primary document linked and dated
1. **About / corrections** — how citizens can submit corrections

-----

## 7. Phased build plan

See section 7 of the original plan; phases 0–9.

-----

## 8. Quality bar and editorial principles

- **Every numeric claim links to a primary source.** No exceptions. If we can't link it, we don't show it.
- **Show your math.** A "details" expander on every computed metric showing inputs and method.
- **Show your gaps.** A red badge on the dashboard showing data freshness and missing-data percentage.
- **Be deeply skeptical of your own pipeline.** Build a manual-review queue for any extraction over a confidence threshold.
- **Don't editorialize on the site itself.** The site presents data with methodology. Opinions go elsewhere.
- **Welcome corrections aggressively.** Public corrections log.

-----

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Outcome data is reported in incompatible units | Tier system; never aggregate across tiers |
| City changes URLs and breaks scrapers | R2 mirror of every source PDF; smoke tests in CI |
| Nonprofits push back on cost-per-beneficiary as unfair | Methodology page anticipates this; offer right-of-reply on every recipient page |
| A single wrong number undermines credibility | Manual review gate for extractions; staging environment; corrections log |
| Site becomes a target in homelessness culture-war content | Strict editorial neutrality; no inflammatory framing; refuse to be a leaderboard |
| Volunteer burnout | Static-file pipeline so site keeps working even if ETL pauses for months |
| Capital vs operating mismatch in PSH | Separate them in the schema from day one; show both in UI |

-----

## 10. What success looks like

- Within 6 months: Denver Auditor's office or a city council office cites the site in a public document.
- Within 12 months: A working journalist files a story using the site as primary research.
- Within 18 months: At least one nonprofit changes how they report outcomes because the site exposed a comparability gap.
- The site never has to retract a published number due to extraction error.
