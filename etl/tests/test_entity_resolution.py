"""Smoke tests for the deterministic vendor-name matcher."""
from __future__ import annotations

from etl.sources.denver_checkbook.entity_resolution import match_vendor, normalize


def test_normalize_strips_suffixes_and_punctuation():
    # "the" is only dropped when it's the leading token
    assert normalize("COLORADO COALITION FOR THE HOMELESS, INC.") == \
        "colorado coalition for the homeless"
    assert normalize("The Salvation Army") == "salvation army"
    assert normalize("  Brothers Redev,  LLC  ") == "brothers redev"


def test_match_distinctive_handles_inc_and_uppercase():
    m = match_vendor("COLORADO COALITION FOR THE HOMELESS, INC.")
    assert m is not None
    assert m.confidence == "distinctive"
    assert m.seed.canonical == "Colorado Coalition for the Homeless"


def test_match_alias_voa():
    m = match_vendor("VOA Colorado Branch Office")
    assert m is not None
    assert m.seed.canonical == "Volunteers of America Colorado"


def test_no_false_match_on_unrelated_vendor():
    assert match_vendor("Acme Office Supplies") is None


def test_st_francis_variants():
    for name in [
        "St. Francis Center",
        "Saint Francis Center",
        "ST FRANCIS CENTER",
    ]:
        m = match_vendor(name)
        assert m is not None, name
        assert m.seed.canonical == "St. Francis Center", name


def test_does_not_overmatch_dha_tokens_in_random_text():
    # 'dha' as a substring inside another word should NOT match — the alias
    # has a trailing space/comma to avoid this. This test pins that behavior.
    assert match_vendor("Random Vendor With dharmaword") is None
