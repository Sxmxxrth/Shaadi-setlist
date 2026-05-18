"""
retrieval — Parse user requests and retrieve matching songs from the dataset.

This module owns the scoring / ranking logic that turns a natural-language
query like ``"baraat, hype, punjabi, gen-z"`` into an ordered list of the
best-matching ``Song`` dicts from the dataset.
"""

from src.aliases import (
    CROWD_ALIASES,
    EVENT_ALIASES,
    MOOD_ALIASES,
    REGION_ALIASES,
    match_tag,
    normalize,
    split_tags,
)
import src.config as config
from src.config import SONGS, LIVE_SEARCH_LIMIT
from src.models import Song
from src.rag import build_query_text, rag_score, tokenize
from src.yt_search import build_live_song_entries


# ── Request parsing ───────────────────────────────────────────────────────────

def parse_request(user_input: str) -> dict:
    """
    Parse a free-form user string into a structured request dict.

    Accepted formats::

        event, mood
        event, mood, region
        event, mood, region, crowd
        event, mood, region=punjabi, crowd=family

    Raises ``ValueError`` if fewer than two tokens are found.
    """
    text = user_input.strip().lower()
    parts = [p.strip() for p in text.split(",") if p.strip()]

    # Allow space-separated input when there are no commas.
    if len(parts) == 1:
        words = parts[0].split()
        if len(words) >= 2:
            parts = [words[0], words[1], *words[2:]]

    if len(parts) < 2:
        raise ValueError("expected at least event and mood")

    request = {
        "event": parts[0],
        "mood": parts[1],
        "region": None,
        "crowd": None,
    }

    for part in parts[2:]:
        if "=" in part:
            key, value = [p.strip() for p in part.split("=", 1)]
            if key in request:
                request[key] = value
            continue

        region = normalize(part, REGION_ALIASES)
        crowd = normalize(part, CROWD_ALIASES)
        if region in REGION_ALIASES:
            request["region"] = region
        elif crowd in CROWD_ALIASES:
            request["crowd"] = crowd

    return request


# ── Scoring helpers ───────────────────────────────────────────────────────────

def energy_fit(energy: int | float, mood: str) -> float:
    """Score how well a song's energy level fits the requested mood."""
    if mood == "emotional":
        return 10 - abs(float(energy) - 3)
    if mood in {"romantic", "classy"}:
        return 10 - abs(float(energy) - 5)
    return float(energy)


# ── Song retrieval ────────────────────────────────────────────────────────────

def filter_songs(
    event: str,
    mood: str,
    region: str | None = None,
    crowd: str | None = None,
) -> list[Song]:
    """
    Return up to 15 best-matched songs (as full dicts) so the LLM gets
    rich context to reason from.
    """
    event_norm = normalize(event, EVENT_ALIASES)
    mood_norm = normalize(mood, MOOD_ALIASES)
    region_norm = normalize(region, REGION_ALIASES) if region else None
    crowd_norm = normalize(crowd, CROWD_ALIASES) if crowd else None

    scored: list[tuple[int, float, float, Song]] = []

    for s in SONGS:
        score: float = 0

        event_tags = split_tags(s.get("event", ""))
        mood_tags = split_tags(s.get("mood", ""))
        event_exact, event_partial = match_tag(event_norm, event_tags, EVENT_ALIASES)
        mood_exact, mood_partial = match_tag(mood_norm, mood_tags, MOOD_ALIASES)

        if event_exact:
            score += 4
            if event_tags and normalize(event_tags[0], EVENT_ALIASES) == event_norm:
                score += 2
        elif event_partial:
            score += 1

        if mood_exact:
            score += 3
            if mood_tags and normalize(mood_tags[0], MOOD_ALIASES) == mood_norm:
                score += 1
        elif mood_partial:
            score += 1

        if region_norm:
            region_tags = (
                split_tags(s.get("region", ""))
                + split_tags(s.get("language", ""))
                + split_tags(s.get("genre", ""))
            )
            region_exact, region_partial = match_tag(region_norm, region_tags, REGION_ALIASES)
            if region_exact:
                score += 2
            elif region_partial:
                score += 1

        if crowd_norm and crowd_norm != "mixed":
            crowd_exact, crowd_partial = match_tag(
                crowd_norm, split_tags(s.get("crowd", "")), CROWD_ALIASES,
            )
            if crowd_exact:
                score += 1
            elif crowd_partial:
                score += 0.5

        if score > 0:
            both_match = int(event_exact and mood_exact)
            scored.append((both_match, score, energy_fit(s.get("energy", 5), mood_norm), s))

    query_tokens = tokenize(build_query_text(event, mood, region=region, crowd=crowd))

    # Sort: exact event+mood first → strongest score → local RAG boost → best energy fit.
    scored.sort(
        key=lambda x: (
            x[0],
            x[1],
            rag_score(x[3], query_tokens),
            x[2],
        ),
        reverse=True,
    )
    matched = [item[3] for item in scored[:15]]

    if not matched and config.ENABLE_LIVE_YOUTUBE_SEARCH:
        return build_live_song_entries(
            event,
            mood,
            region=region,
            crowd=crowd,
            limit=LIVE_SEARCH_LIMIT,
        )

    return matched
