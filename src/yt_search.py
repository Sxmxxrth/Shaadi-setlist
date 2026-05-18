"""
yt_search — Live YouTube search fallback for missing dataset matches.

This module uses yt-dlp to search for wedding-related songs on YouTube
and returns lightweight song candidates when the local dataset has no
strong matches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Song

yt_dlp = None
SEARCH_SUFFIX = "wedding song"
DEFAULT_LIMIT = 8


def build_search_query(event: str, mood: str, region: str | None = None, crowd: str | None = None) -> str:
    """Build a simple YouTube search query from the user request."""
    parts = [event.strip(), mood.strip()]
    if region:
        parts.append(region.strip())
    if crowd:
        parts.append(crowd.strip())
    parts.append(SEARCH_SUFFIX)
    return " ".join([part for part in parts if part])


def search_youtube_titles(query: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """Search YouTube for video titles using yt-dlp."""
    global yt_dlp
    if yt_dlp is None:
        try:
            import yt_dlp as _yt_dlp
        except ImportError as exc:
            raise RuntimeError("yt-dlp is required for live YouTube search") from exc
        yt_dlp = _yt_dlp

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": "in_playlist",
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    entries = info.get("entries", []) if isinstance(info, dict) else []
    return [entry.get("title", "").strip() for entry in entries if entry and entry.get("title")]


def build_live_song_entries(
    event: str,
    mood: str,
    region: str | None = None,
    crowd: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list["Song"]:
    """Return lightweight Song dicts from live YouTube search results."""
    query = build_search_query(event, mood, region=region, crowd=crowd)
    titles = search_youtube_titles(query, limit=limit)

    songs: list["Song"] = []
    for title in titles:
        songs.append(
            {
                "song": title,
                "event": "live search",
                "mood": mood,
                "genre": "live search",
                "energy": 5,
                "crowd": crowd or "mixed",
            }
        )
    return songs
