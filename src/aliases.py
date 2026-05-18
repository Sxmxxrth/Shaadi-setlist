"""
aliases — Synonym maps and tag-matching helpers.

Wedding events, moods, regions, and crowd types each have many informal
spellings and near-synonyms.  The alias dictionaries map every variant to
a single canonical key, and the helper functions normalise / compare tags
using those maps.
"""

import re


# ── Alias dictionaries ───────────────────────────────────────────────────────

EVENT_ALIASES: dict[str, list[str]] = {
    "mehendi":   ["mehendi", "mehndi", "henna"],
    "haldi":     ["haldi", "turmeric"],
    "sangeet":   ["sangeet", "sangeeth", "music night"],
    "wedding":   ["wedding", "shaadi", "ceremony", "pheras"],
    "baraat":    ["baraat", "baaraat", "groom entry", "procession"],
    "reception": ["reception", "party"],
    "bidaai":    ["bidaai", "vidaai"],
    "cocktail":  ["cocktail", "pre-party", "evening"],
    "garba":     ["garba", "dandiya"],
}

MOOD_ALIASES: dict[str, list[str]] = {
    "high energy":  ["high energy", "hype", "energetic", "upbeat", "party", "dance"],
    "romantic":     ["romantic", "love", "couple", "soft", "dreamy", "slow"],
    "emotional":    ["emotional", "sad", "teary", "sentimental", "feeling"],
    "fun":          ["fun", "funny", "light", "casual", "playful"],
    "classy":       ["classy", "elegant", "sophisticated", "sufi", "indie"],
    "traditional":  ["traditional", "folk", "ritual", "family"],
    "spiritual":    ["spiritual", "devotional", "sufi", "qawwali"],
}

REGION_ALIASES: dict[str, list[str]] = {
    "punjabi":      ["punjabi", "punjab"],
    "bhangra":      ["bhangra"],
    "gujarati":     ["gujarati", "gujarat", "garba", "dandiya"],
    "marathi":      ["marathi", "maharashtrian", "maharashtra"],
    "haryanvi":     ["haryanvi", "haryana"],
    "north indian": ["north indian", "north india"],
    "south indian": ["south indian", "tamil", "telugu", "kannada", "malayalam"],
    "bhojpuri":     ["bhojpuri"],
    "bengali":      ["bengali", "bangla"],
    "rajasthani":   ["rajasthani", "rajasthan"],
    "bollywood":    ["bollywood", "hindi"],
}

CROWD_ALIASES: dict[str, list[str]] = {
    "family": ["family", "parents", "relatives"],
    "gen-z":  ["gen-z", "gen z", "genz", "young", "friends"],
    "elders": ["elders", "older", "senior"],
    "mixed":  ["mixed", "everyone", "all ages"],
}


def _tokenize(text: str) -> list[str]:
    return [token for token in __import__("re").findall(r"[a-z0-9]+", str(text).lower())]


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize(term: str, alias_map: dict[str, list[str]]) -> str:
    """Return the canonical key if *term* matches any alias, else return it as-is."""
    term = str(term or "").strip().lower()
    if not term:
        return term

    for canonical, aliases in alias_map.items():
        for alias in aliases:
            alias_text = str(alias or "").strip().lower()
            if term == alias_text:
                return canonical
            if alias_text.replace("-", " ") == term:
                return canonical
            if " " in alias_text and term in _tokenize(alias_text):
                return canonical
            if " " in term and alias_text in _tokenize(term):
                return canonical

    return term


def split_tags(value: str) -> list[str]:
    """Split a comma-separated tag string into a cleaned list of lowercase tags."""
    return [item.strip().lower() for item in str(value or "").split(",") if item.strip()]


def _has_token_overlap(a: str, b: str) -> bool:
    a_tokens = set(_tokenize(a))
    b_tokens = set(_tokenize(b))
    return bool(a_tokens & b_tokens)


def match_tag(term: str, tags: list[str], alias_map: dict[str, list[str]]) -> tuple[bool, bool]:
    """Return ``(exact_match, partial_match)`` after normalising both sides."""
    term_norm = normalize(term, alias_map)
    tag_norms = [normalize(tag, alias_map) for tag in tags]
    exact = term_norm in tag_norms
    partial = any(_has_token_overlap(term_norm, tag) for tag in tag_norms)
    return exact, partial
