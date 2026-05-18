"""Tests for alias normalization and tag matching."""

from src.aliases import normalize, match_tag, EVENT_ALIASES, MOOD_ALIASES, CROWD_ALIASES


def test_normalize_exact_aliases():
    assert normalize("pre-party", EVENT_ALIASES) == "cocktail"
    assert normalize("Gen z", CROWD_ALIASES) == "gen-z"
    assert normalize("mehndi", EVENT_ALIASES) == "mehendi"
    assert normalize("sad", MOOD_ALIASES) == "emotional"


def test_normalize_multiword_alias_token_match():
    assert normalize("music", EVENT_ALIASES) == "sangeet"
    assert normalize("music night", EVENT_ALIASES) == "sangeet"


def test_normalize_does_not_confuse_substrings():
    assert normalize("party", EVENT_ALIASES) != "cocktail"
    assert normalize("party", MOOD_ALIASES) == "high energy"


def test_match_tag_partial_token_overlap():
    exact, partial = match_tag("high energy", ["energetic"], MOOD_ALIASES)
    assert exact is True

    exact, partial = match_tag("high", ["high energy"], {})
    assert exact is False
    assert partial is True
