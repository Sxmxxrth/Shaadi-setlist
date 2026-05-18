"""
playlist_service — Shared playlist orchestration for CLI and Gradio.

The UI layers should stay thin. This module owns the full request flow:
parse input, retrieve/RAG-rank songs, build the LLM prompt, verify output,
and return a structured result that callers can render however they like.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

import src.config as config
from src.config import SONGS
from src.models import Song
from src.playlist import build_prompt, generate_playlist
from src.retrieval import filter_songs, parse_request


@dataclass
class PlaylistResult:
    """Structured response for playlist generation."""

    request: dict | None = None
    matched_songs: list[Song] = field(default_factory=list)
    playlist: str = ""
    verified_songs: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def extract_verified_songs(reply: str, songs: list[dict] | None = None) -> list[str]:
    """
    Parse numbered song names from an LLM reply and keep only dataset titles.

    This protects downloads from hallucinated or heavily annotated song names.
    """
    dataset = songs or SONGS
    titles_by_lower = {song["song"].strip().lower(): song["song"].strip() for song in dataset}
    raw = [
        name.strip()
        for name in re.findall(r"^\d+\.\s+([^\n]+)", reply or "", re.MULTILINE)
        if name.strip()
    ]

    cleaned: list[str] = []
    for name in raw:
        name = name.strip().strip("*").strip()
        name = re.sub(r"^(?:Song\s*Name\s*:\s*|Song\s*:\s*)", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s*\(.*$", "", name).strip()
        name = re.sub(r"\s*[\-–—]\s+\S.*$", "", name).strip()
        name = name.strip("* ").strip()
        canonical = titles_by_lower.get(name.lower())
        if canonical:
            cleaned.append(canonical)

    return list(dict.fromkeys(cleaned))


def generate_playlist_result(user_input: str, enable_live_search: bool = False) -> PlaylistResult:
    """Run the complete playlist workflow and return a structured result."""
    previous_live_search = config.ENABLE_LIVE_YOUTUBE_SEARCH
    config.ENABLE_LIVE_YOUTUBE_SEARCH = enable_live_search

    try:
        request = parse_request(user_input)
    except ValueError:
        config.ENABLE_LIVE_YOUTUBE_SEARCH = previous_live_search
        return PlaylistResult(
            playlist="Format: event, mood[, region][, crowd] e.g. sangeet, hype, punjabi, family",
            error="Please enter at least an event and mood.",
        )

    try:
        matched = filter_songs(
            request["event"],
            request["mood"],
            region=request["region"],
            crowd=request["crowd"],
        )
    finally:
        config.ENABLE_LIVE_YOUTUBE_SEARCH = previous_live_search

    if not matched:
        return PlaylistResult(
            request=request,
            matched_songs=[],
            playlist="No strong dataset matches were found. Try a broader mood or enable live search.",
            error="No matching songs found.",
        )

    # Retrieval already applies the local RAG boost before the LLM prompt is built.
    final_prompt = build_prompt(request, matched)

    try:
        playlist = generate_playlist(final_prompt)
    except Exception as exc:
        return PlaylistResult(
            request=request,
            matched_songs=matched,
            playlist=f"AI playlist unavailable: {exc}\n\nThe matched songs are still valid dataset recommendations.",
            verified_songs=[song["song"] for song in matched],
            error=str(exc),
        )

    return PlaylistResult(
        request=request,
        matched_songs=matched,
        playlist=playlist,
        verified_songs=extract_verified_songs(playlist),
    )


def process_query(user_input: str, enable_live_search: bool = False) -> tuple[str, list[str]]:
    """Backward-compatible tuple API used by older UI code."""
    result = generate_playlist_result(user_input, enable_live_search=enable_live_search)
    return result.playlist, result.verified_songs
