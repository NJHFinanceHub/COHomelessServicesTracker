-- Denver Homelessness Dollar Tracker — canonical schema (v1, SQLite)
--
-- Design notes:
-- * Money and outcomes are kept in separate tables and only joined through
--   `cost_allocation`, which forces every join to declare an explicit
--   `allocation_method`. This is the load-bearing wall of the model.
-- * Every row that asserts a number carries a source_url and (where relevant)
--   a source_doc_page. Nothing on the public site is rendered without one.
-- * Service categories carry an explicit unit_of_service so that per-unit
--   math is impossible to apply across incompatible categories.
-- * v1 is SQLite; types are mostly TEXT/REAL/INTEGER. Date columns are ISO-8601
--   TEXT to keep things grep-able.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Funding flow: sources → appropriations → agencies → contracts → payments
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS funding_source (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL CHECK (type IN (
                        'federal', 'state', 'local-tax', 'bond',
                        'philanthropic', 'fee', 'other'
                    )),
    legal_authority TEXT,             -- e.g. "Ballot 2B 2020"
    description     TEXT,
    source_url      TEXT
);

CREATE TABLE IF NOT EXISTS agency (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,     -- HOST, DPD, DDPHE, DHA, etc.
    parent  TEXT NOT NULL CHECK (parent IN (
                'city', 'state', 'federal', 'regional'
            )),
    notes   TEXT
);

CREATE TABLE IF NOT EXISTS appropriation (
    id                     INTEGER PRIMARY KEY,
    funding_source_id      INTEGER NOT NULL REFERENCES funding_source(id),
    fiscal_year            INTEGER NOT NULL,
    amount                 REAL    NOT NULL,
    recipient_agency_id    INTEGER NOT NULL REFERENCES agency(id),
    source_doc_url         TEXT    NOT NULL,
    source_doc_page        INTEGER,
    extraction_confidence  TEXT CHECK (extraction_confidence IN (
                               'manual', 'auto-high', 'auto-medium', 'auto-low'
                           )),
    notes                  TEXT
);
CREATE INDEX IF NOT EXISTS idx_appropriation_year
    ON appropriation(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_appropriation_agency
    ON appropriation(recipient_agency_id);

CREATE TABLE IF NOT EXISTS recipient (
    id                      INTEGER PRIMARY KEY,
    legal_name              TEXT NOT NULL,
    dba_names               TEXT,    -- JSON array of strings
    ein                     TEXT UNIQUE,
    address                 TEXT,
    naics                   TEXT,
    is_nonprofit            INTEGER CHECK (is_nonprofit IN (0, 1)),
    fiscal_year_end         TEXT,    -- MM-DD
    state_of_incorporation  TEXT,
    propublica_id           TEXT,
    url                     TEXT
);
CREATE INDEX IF NOT EXISTS idx_recipient_legal_name
    ON recipient(legal_name);

CREATE TABLE IF NOT EXISTS service_category (
    id               INTEGER PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    parent_id        INTEGER REFERENCES service_category(id),
    unit_of_service  TEXT NOT NULL,
    -- e.g.:
    --   "Emergency Shelter"             → "bed-night"
    --   "Permanent Supportive Housing"  → "household-month-housed"
    --   "Rapid Rehousing"               → "household-placed"
    --   "Eviction Prevention"           → "household-stabilized"
    --   "Street Outreach"               → "contact"
    --   "Day Services"                  → "visit"
    description      TEXT
);

CREATE TABLE IF NOT EXISTS contract (
    id                    INTEGER PRIMARY KEY,
    agency_id             INTEGER NOT NULL REFERENCES agency(id),
    recipient_id          INTEGER NOT NULL REFERENCES recipient(id),
    contract_number       TEXT,
    title                 TEXT,
    start_date            TEXT,    -- ISO date
    end_date              TEXT,
    total_value           REAL,
    executed_amount       REAL,
    service_category_id   INTEGER REFERENCES service_category(id),
    source_url            TEXT,
    council_resolution_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_contract_recipient
    ON contract(recipient_id);
CREATE INDEX IF NOT EXISTS idx_contract_agency
    ON contract(agency_id);

CREATE TABLE IF NOT EXISTS payment (
    id              INTEGER PRIMARY KEY,
    contract_id     INTEGER REFERENCES contract(id),  -- nullable; not every payment maps to a contract
    agency_id       INTEGER NOT NULL REFERENCES agency(id),
    recipient_id    INTEGER NOT NULL REFERENCES recipient(id),
    payment_date    TEXT NOT NULL,
    amount          REAL NOT NULL,
    fund_code       TEXT,
    object_code     TEXT,
    description     TEXT,
    source_dataset  TEXT NOT NULL,    -- e.g. "denver_checkbook:wnau-xrqi"
    source_row_id   TEXT NOT NULL,    -- upstream row id, for idempotency
    UNIQUE (source_dataset, source_row_id)
);
CREATE INDEX IF NOT EXISTS idx_payment_recipient
    ON payment(recipient_id);
CREATE INDEX IF NOT EXISTS idx_payment_date
    ON payment(payment_date);

-- ---------------------------------------------------------------------------
-- Operational + outcome layer: programs and what they produced
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS program (
    id                   INTEGER PRIMARY KEY,
    recipient_id         INTEGER NOT NULL REFERENCES recipient(id),
    name                 TEXT NOT NULL,
    service_category_id  INTEGER NOT NULL REFERENCES service_category(id),
    location             TEXT,
    target_population    TEXT,
    notes                TEXT
);
CREATE INDEX IF NOT EXISTS idx_program_recipient
    ON program(recipient_id);

CREATE TABLE IF NOT EXISTS outcome_report (
    id                    INTEGER PRIMARY KEY,
    program_id            INTEGER NOT NULL REFERENCES program(id),
    period_start          TEXT NOT NULL,
    period_end            TEXT NOT NULL,
    units_served          REAL,    -- in the program's unit_of_service
    unique_individuals    INTEGER,
    unique_households     INTEGER,
    housed_at_period_end  INTEGER,
    source_url            TEXT NOT NULL,
    source_doc_page       INTEGER,
    reporting_standard    TEXT NOT NULL CHECK (reporting_standard IN (
                              'HMIS', 'self-reported', 'HUD-CAPER',
                              'HOST-quarterly', 'mayors-dashboard', 'other'
                          )),
    data_quality_score    INTEGER CHECK (data_quality_score BETWEEN 0 AND 100)
);
CREATE INDEX IF NOT EXISTS idx_outcome_program
    ON outcome_report(program_id);
CREATE INDEX IF NOT EXISTS idx_outcome_period
    ON outcome_report(period_start, period_end);

-- ---------------------------------------------------------------------------
-- The bridge: how dollars map to programs
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cost_allocation (
    id                  INTEGER PRIMARY KEY,
    payment_id          INTEGER REFERENCES payment(id),
    appropriation_id    INTEGER REFERENCES appropriation(id),
    program_id          INTEGER NOT NULL REFERENCES program(id),
    allocation_method   TEXT NOT NULL CHECK (allocation_method IN (
                            'direct',     -- contract or invoice line is program-specific
                            'pro-rata',   -- split by program budget weights
                            'estimated',  -- our best guess; flag in UI
                            'capital',    -- one-time capital, separated from operating
                            'overhead'    -- admin allocation
                        )),
    allocated_amount    REAL NOT NULL,
    allocator_notes     TEXT,
    CHECK ((payment_id IS NOT NULL) <> (appropriation_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_alloc_program
    ON cost_allocation(program_id);
CREATE INDEX IF NOT EXISTS idx_alloc_payment
    ON cost_allocation(payment_id);
CREATE INDEX IF NOT EXISTS idx_alloc_approp
    ON cost_allocation(appropriation_id);

-- ---------------------------------------------------------------------------
-- 990 financials (ProPublica Nonprofit Explorer)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS org_financials (
    id                  INTEGER PRIMARY KEY,
    recipient_id        INTEGER NOT NULL REFERENCES recipient(id),
    fiscal_year         INTEGER NOT NULL,
    total_revenue       REAL,
    total_expenses      REAL,
    program_expenses    REAL,
    mgmt_expenses       REAL,
    fundraising_expenses REAL,
    exec_comp_top1      REAL,
    govt_grants         REAL,
    source_url          TEXT NOT NULL,
    UNIQUE (recipient_id, fiscal_year)
);

-- ---------------------------------------------------------------------------
-- Provenance: every fetch we ever did
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS source_fetch (
    id              INTEGER PRIMARY KEY,
    source_name     TEXT NOT NULL,            -- e.g. "denver_checkbook"
    fetched_at      TEXT NOT NULL,            -- ISO timestamp
    url             TEXT NOT NULL,
    http_status     INTEGER,
    bytes           INTEGER,
    sha256          TEXT,
    raw_path        TEXT,                     -- relative path under data/raw
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetch_source
    ON source_fetch(source_name, fetched_at);
