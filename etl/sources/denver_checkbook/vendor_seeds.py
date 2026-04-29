"""
Curated seed list of homelessness-related Denver-area nonprofit recipients.

Each entry has:
  - canonical: the legal name we'll store as `recipient.legal_name`
  - aliases:   substrings the city has historically used in checkbook
               vendor strings. Match is case-insensitive substring against a
               normalized vendor name (see `entity_resolution.normalize`).
  - distinctive: a single distinctive substring that we trust as a
               high-confidence match even without further checks.
  - notes:     short human note for reviewers

Hand-curated; expect this list to grow. The list itself is not the source of
truth for whether a payment counts — the *match* is recorded with a
confidence score that the reviewer can override.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class VendorSeed:
    canonical: str
    distinctive: str
    aliases: List[str] = field(default_factory=list)
    notes: str = ""


SEEDS: List[VendorSeed] = [
    VendorSeed(
        canonical="Colorado Coalition for the Homeless",
        distinctive="coalition for the homeless",
        aliases=["colorado coalition", "cch ", "cch,"],
        notes="Largest single recipient historically; runs Stout Street, PSH portfolio.",
    ),
    VendorSeed(
        canonical="Volunteers of America Colorado",
        distinctive="volunteers of america",
        aliases=["voa colorado", "voa,"],
        notes="Family shelter, women's shelter, 48th Ave bridge housing.",
    ),
    VendorSeed(
        canonical="St. Francis Center",
        distinctive="st. francis center",
        aliases=["saint francis center", "st francis center"],
        notes="Day shelter and employment services.",
    ),
    VendorSeed(
        canonical="Catholic Charities of Denver",
        distinctive="catholic charities",
        aliases=["catholic charities of denver", "samaritan house"],
        notes="Operates Samaritan House emergency shelter.",
    ),
    VendorSeed(
        canonical="Bayaud Enterprises",
        distinctive="bayaud",
        aliases=["bayaud enterprises"],
        notes="Vocational rehab + day services.",
    ),
    VendorSeed(
        canonical="Mile High Behavioral Healthcare",
        distinctive="mile high behavioral",
        aliases=["mile high behavioral health"],
        notes="Behavioral health + shelter operations.",
    ),
    VendorSeed(
        canonical="Urban Peak",
        distinctive="urban peak",
        aliases=["urban peak denver"],
        notes="Youth-specific homelessness services.",
    ),
    VendorSeed(
        canonical="Denver Rescue Mission",
        distinctive="denver rescue mission",
        aliases=["rescue mission", "drm "],
        notes="Lawrence Street shelter, Crossing.",
    ),
    VendorSeed(
        canonical="The Salvation Army",
        distinctive="salvation army",
        aliases=["crossroads shelter", "salvation army crossroads"],
        notes="Operates Crossroads shelter for the city.",
    ),
    VendorSeed(
        canonical="Brothers Redevelopment, Inc.",
        distinctive="brothers redevelopment",
        aliases=["brothers redev", "bri inc"],
        notes="Eviction prevention, housing counseling.",
    ),
    VendorSeed(
        canonical="WellPower (Mental Health Center of Denver)",
        distinctive="wellpower",
        aliases=["mental health center of denver", "mhcd"],
        notes="Re-branded from MHCD; behavioral health partner.",
    ),
    VendorSeed(
        canonical="The Gathering Place",
        distinctive="gathering place",
        aliases=["the gathering place"],
        notes="Day shelter for women, children, transgender individuals.",
    ),
    VendorSeed(
        canonical="Denver Housing Authority",
        distinctive="denver housing authority",
        aliases=["dha ", "dha,"],
        notes="Quasi-public; receives city pass-through for PSH and vouchers.",
    ),
    VendorSeed(
        canonical="Metro Denver Homeless Initiative",
        distinctive="metro denver homeless",
        aliases=["mdhi ", "mdhi,"],
        notes="HUD-designated CoC; runs HMIS and PIT count.",
    ),
    VendorSeed(
        canonical="Denver Indian Health and Family Services",
        distinctive="denver indian health",
        aliases=["dihfs"],
        notes="Culturally-specific services for AI/AN community.",
    ),
    VendorSeed(
        canonical="Senior Support Services",
        distinctive="senior support services",
        aliases=[],
        notes="Older-adult-focused day services.",
    ),
    VendorSeed(
        canonical="Delores Project",
        distinctive="delores project",
        aliases=["the delores project"],
        notes="Shelter for unaccompanied women and transgender individuals.",
    ),
    VendorSeed(
        canonical="Family Promise of Greater Denver",
        distinctive="family promise",
        aliases=[],
        notes="Family shelter network.",
    ),
    VendorSeed(
        canonical="Florence Crittenton Services of Colorado",
        distinctive="florence crittenton",
        aliases=[],
        notes="Teen-parent supports including housing.",
    ),
    VendorSeed(
        canonical="Hope Communities, Inc.",
        distinctive="hope communities",
        aliases=[],
        notes="Affordable housing developer + supportive services.",
    ),
    VendorSeed(
        canonical="Mercy Housing Mountain Plains",
        distinctive="mercy housing",
        aliases=[],
        notes="Affordable housing developer with supportive housing portfolio.",
    ),
    VendorSeed(
        canonical="The Empowerment Program",
        distinctive="empowerment program",
        aliases=[],
        notes="Re-entry and housing for women.",
    ),
    VendorSeed(
        canonical="Servicios de la Raza",
        distinctive="servicios de la raza",
        aliases=[],
        notes="Latino-focused supports including housing navigation.",
    ),
    VendorSeed(
        canonical="Denver Inner City Parish",
        distinctive="denver inner city parish",
        aliases=["dicp "],
        notes="Direct services in west Denver.",
    ),
    VendorSeed(
        canonical="Volunteers of America National (capital partner)",
        distinctive="voa national",
        aliases=[],
        notes="Capital partner for some PSH developments; flag and verify.",
    ),
    VendorSeed(
        canonical="Saint Francis Apartments / Saint Francis Center Housing",
        distinctive="saint francis apartments",
        aliases=["st francis apartments", "st. francis apartments"],
        notes="PSH operating arm of St. Francis Center.",
    ),
    VendorSeed(
        canonical="Denver Basic Income Project",
        distinctive="basic income project",
        aliases=["dbip "],
        notes="Direct cash transfer pilot for unhoused residents.",
    ),
    VendorSeed(
        canonical="Stride Community Health Center",
        distinctive="stride community health",
        aliases=["stride chc"],
        notes="Healthcare for the homeless partner.",
    ),
    VendorSeed(
        canonical="Cross Purpose",
        distinctive="cross purpose",
        aliases=[],
        notes="Workforce + economic mobility, not strictly homelessness; flag.",
    ),
    VendorSeed(
        canonical="Tiny Homes / Beloved Community Village (operator)",
        distinctive="beloved community village",
        aliases=["colorado village collaborative", "cvc "],
        notes="Operator: Colorado Village Collaborative — tiny-home villages.",
    ),
]
