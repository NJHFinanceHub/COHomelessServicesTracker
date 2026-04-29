# Methodology — v0.1 (draft)

> Status: draft. Updated transparently as the data model is stress-tested. Public versioning lives in [`docs/changelog.md`](./changelog.md).

This site traces taxpayer dollars Denver spends on homelessness from their source to their reported outcomes. We compute **cost-per-unit metrics within comparable service categories** — never a single "cost per homeless person" number. This page explains exactly how we do it, what we will not do, and why.

## The problem with a single headline number

The tempting headline — "Denver spends $X per homeless person" — is almost always wrong. Three reasons:

1. **The denominator is the wrong shape.** The Point-in-Time (PIT) count is a one-night snapshot. Total annual spending serves a much larger annual cohort with high turnover. Dividing one by the other inflates the apparent per-person cost by a large and unknowable factor.
2. **The numerator mixes incompatible units.** A bed-night in emergency shelter, a household placed in rapid rehousing, an outreach contact, and a permanent supportive housing unit are not the same thing. They cost different amounts, serve different populations, and produce different outcomes.
3. **Capital and operating spending get blurred.** A $40M building is a one-time cost that serves residents for decades. Adding it to a single year's operating costs creates a number that looks bad and is meaningless.

We therefore compute per-unit costs **only within comparable service categories**, and we present them with explicit confidence tiers.

## The flow we model

```
Funding source  →  Appropriation  →  City agency  →  Contract  →  Payment
                                                                     │
                                                                     ▼
                                                              Cost allocation
                                                                     │
                                                                     ▼
                                                                  Program  ◀──  Outcome report
```

Every dollar on the site is anchored to:

- a **funding source** (e.g., Homelessness Resolution Fund — Ballot 2B 2020)
- an **appropriation** in a budget document (cited by URL and page)
- a **city agency** that received it (HOST, DDPHE, DPD, etc.)
- a **contract** or direct expenditure (cited to Legistar resolution where possible)
- a **payment** in the Denver Open Checkbook (cited by row id)
- a **cost allocation** that maps the payment to one or more programs with an explicit method

Every reported outcome is anchored to:

- a **program** run by a recipient
- an **outcome report** with a clearly labeled unit (bed-night, household, person-housed, contact)
- a **reporting standard** (HMIS, HUD CAPER, HOST quarterly, Mayor's dashboard, self-reported)
- a **source document** with URL and page

## Service categories and units

Each service category has a single declared unit of service. We do not let the system add units across categories.

| Service category | Unit of service |
|---|---|
| Emergency Shelter | bed-night |
| Transitional / Bridge Housing | household-month-sheltered |
| Rapid Rehousing | household-placed |
| Permanent Supportive Housing (operating) | household-month-housed |
| Permanent Supportive Housing (capital) | unit-developed |
| Eviction Prevention | household-stabilized (12+ months) |
| Street Outreach | contact (input metric only) |
| Day Services | visit |

Capital and operating spend on PSH are tracked separately and shown separately. Outreach contacts are input metrics and are never converted into housing-outcome equivalents.

## The three confidence tiers

| Tier | Definition | What we publish |
|---|---|---|
| **Tier 1 — directly comparable** | Same service category, same reporting standard (HMIS preferred), same period, allocation method `direct` | Ranges and medians within the tier |
| **Tier 2 — comparable with caveats** | Same category, mixed reporting standards or `pro-rata` allocations | Numbers shown with a confidence flag |
| **Tier 3 — informational only** | Cross-category, self-reported only, or `estimated` allocation | Shown but never aggregated |

Aggregation is never permitted across tiers.

## Cost allocation methods

A single payment to a multi-program nonprofit cannot be naively divided by total beneficiaries. Every allocation row in our `cost_allocation` table declares one of:

- **`direct`** — the payment or invoice line is program-specific and identifiable in the source document
- **`pro-rata`** — split across programs by published program budget weights
- **`estimated`** — our best guess based on available evidence; flagged prominently in the UI
- **`capital`** — one-time capital spend, separated from operating
- **`overhead`** — admin and management overhead, allocated by 990 ratios

The UI shows the allocation method on every computed metric. If a number depends on `estimated` allocations, it is flagged with a yellow indicator and excluded from Tier 1.

## What we deliberately do not do

- **Do not** compute "cost per homeless person" by dividing total spending by PIT count.
- **Do not** subtract capital from operating without flagging the change.
- **Do not** compare a low-acuity day-services org to a high-acuity PSH provider on cost-per-person.
- **Do not** name-and-shame outliers without first looking at program mix and acuity.
- **Do not** publish a number that cannot be linked back to a primary source.

## Corrections and right of reply

Every nonprofit recipient on the site has a profile page with a "submit a correction" link that opens a public GitHub issue. Corrections are reviewed openly and resolved with a visible audit trail. Substantive numerical corrections are noted in `docs/changelog.md`.

## Versioning

This methodology is versioned. Material changes (new tier definitions, new categories, new allocation methods) bump the version and are recorded in `docs/changelog.md`.

— v0.1, Phase 0 scaffold.
