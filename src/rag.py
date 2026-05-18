"""
rag — Lightweight local retrieval augmentation over the song dataset.

This is intentionally small and dependency-free: it builds an in-memory
token index from the curated song metadata, then uses token overlap as a
semantic-ish boost before the LLM prompt is built.
"""

import re
from functools import lru_cache
from typing import Iterable

from src.aliases import (
    CROWD_ALIASES,
    EVENT_ALIASES,
    MOOD_ALIASES,
    REGION_ALIASES,
    normalize,
)
from src.config import SONGS
from src.models import Song

INDEX_FIELDS = (
    "song",
    "event",
    "mood",
    "genre",
    "region",
    "language",
    "crowd",
    "moment",
    "notes",
)


def tokenize(text: str) -> set[str]:
    """Return normalized word tokens for simple local retrieval."""
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def _metadata_text(song: Song) -> str:
    return " ".join(str(song.get(field, "")) for field in INDEX_FIELDS)


@lru_cache(maxsize=1)
def build_index() -> tuple[dict, ...]:
    """Build the local RAG index once per process."""
    return tuple(
        {
            "song": song,
            "tokens": tokenize(_metadata_text(song)),
        }
        for song in SONGS
    )


def build_query_text(event: str, mood: str, region: str | None = None, crowd: str | None = None) -> str:
    """Expand the user request with canonical aliases for better local matching."""
    parts = [
        event,
        normalize(event, EVENT_ALIASES),
        mood,
        normalize(mood, MOOD_ALIASES),
    ]
    if region:
        parts.extend([region, normalize(region, REGION_ALIASES)])
    if crowd:
        parts.extend([crowd, normalize(crowd, CROWD_ALIASES)])
    return " ".join(part for part in parts if part)


def rag_score(song: Song, query_tokens: Iterable[str]) -> float:
    """Score one song by overlap between request tokens and indexed metadata."""
    token_set = set(query_tokens)
    if not token_set:
        return 0.0

    for item in build_index():
        if item["song"] is song:
            overlap = token_set & item["tokens"]
            return len(overlap) / max(len(token_set), 1)
    return 0.0


def rank_with_rag(songs: list[Song], query_text: str, limit: int = 15) -> list[Song]:
    """
    Re-rank already retrieved candidates using local metadata overlap.

    The classic scoring in retrieval.py remains primary; this only nudges
    similarly scored songs toward titles whose metadata best matches the
    request context used for the LLM prompt.
    """
    query_tokens = tokenize(query_text)
    if not songs or not query_tokens:
        return songs[:limit]

    ranked = sorted(
        enumerate(songs),
        key=lambda item: (rag_score(item[1], query_tokens), -item[0]),
        reverse=True,
    )
    return [song for _, song in ranked[:limit]]


def search_dataset(query_text: str, limit: int = 15) -> list[Song]:
    """Return dataset songs that best match an arbitrary local RAG query."""
    query_tokens = tokenize(query_text)
    if not query_tokens:
        return []

    scored: list[tuple[float, Song]] = []
    for item in build_index():
        score = len(query_tokens & item["tokens"])
        if score:
            scored.append((score, item["song"]))

    scored.sort(key=lambda item: (item[0], item[1].get("energy", 0)), reverse=True)
    return [song for _, song in scored[:limit]]
