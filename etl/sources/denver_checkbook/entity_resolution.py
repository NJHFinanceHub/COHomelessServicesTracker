"""
Entity resolution for Denver Checkbook vendor strings.

The checkbook stores the vendor name verbatim, so the same nonprofit shows up
under many forms — "Colorado Coalition for the Homeless", "COLORADO COALITION
FOR THE HOMELESS, INC", "Colo. Coalition Homeless Inc". A single fuzzy-match
library would conflate too many distinct organizations (e.g. "Catholic
Charities of the Archdiocese of Denver" vs. "Catholic Charities USA"), so we
do a deterministic two-stage match:

1. **Normalize** the vendor string: lowercase, strip punctuation, collapse
   whitespace, drop trailing corporate suffixes ("inc", "llc", "corp",
   "co", "ltd", "the").
2. **Match against curated seed substrings** (`vendor_seeds.SEEDS`).
   Confidence ladder:
       'distinctive' — distinctive substring present
       'alias'       — one of the explicit aliases present
       'none'        — no match

The result is structured so a human reviewer can flip a 'distinctive' match
to a confirmed `recipient_id` once and never re-review it.

This is deliberately narrow. Names not on the seed list will show up in a
"new candidates" report and require a curator to add them. That's a feature:
it prevents the matcher from silently expanding scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .vendor_seeds import SEEDS, VendorSeed


_SUFFIX_TOKENS = {
    "inc",
    "inc.",
    "llc",
    "l.l.c.",
    "corp",
    "corp.",
    "corporation",
    "co",
    "co.",
    "company",
    "ltd",
    "ltd.",
    "limited",
}
_PUNCT_RE = re.compile(r"[^\w\s\-]")
_WS_RE = re.compile(r"\s+")


def normalize(vendor_name: str) -> str:
    """Lowercase, strip punctuation, drop common corporate suffixes."""
    if not vendor_name:
        return ""
    s = vendor_name.lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    tokens = [t for t in s.split(" ") if t and t not in _SUFFIX_TOKENS]
    # Drop a leading "the" for matching purposes
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    return " ".join(tokens)


@dataclass(frozen=True)
class Match:
    seed: VendorSeed
    confidence: str  # 'distinctive' | 'alias'
    matched_on: str  # the normalized phrase that triggered the match


def _phrase_in_tokens(phrase: str, tokens: List[str]) -> bool:
    """True iff `phrase` (already normalized) is a consecutive sub-sequence
    of `tokens`. Whole-token matching avoids "dha" matching "dharmaword"."""
    p_tokens = phrase.split()
    if not p_tokens:
        return False
    n = len(p_tokens)
    for i in range(0, len(tokens) - n + 1):
        if tokens[i : i + n] == p_tokens:
            return True
    return False


def match_vendor(vendor_name: str) -> Optional[Match]:
    """Return the best Match for a vendor string, or None.

    Matching is whole-token, not substring: an alias of "dha" matches
    "dha housing" but not "dharma project".
    """
    norm = normalize(vendor_name)
    if not norm:
        return None
    tokens = norm.split()

    # Distinctive phrase is the strongest signal; check first across all seeds.
    for seed in SEEDS:
        d = normalize(seed.distinctive)
        if d and _phrase_in_tokens(d, tokens):
            return Match(seed=seed, confidence="distinctive", matched_on=d)

    # Then aliases.
    for seed in SEEDS:
        for alias in seed.aliases:
            a = normalize(alias)
            if a and _phrase_in_tokens(a, tokens):
                return Match(seed=seed, confidence="alias", matched_on=a)

    return None


def all_seed_canonicals() -> List[str]:
    return [s.canonical for s in SEEDS]
