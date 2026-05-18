"""
playlist — LLM prompt building, playlist generation, and output formatting.

This module talks to the local Ollama API and formats both the prompt
sent to the model and the song lists shown to the user.
"""

import json
from urllib import error, request

from src.aliases import split_tags
from src.config import API_URL, BASE_PROMPT, MODEL
from src.models import Song


# ── Formatting ────────────────────────────────────────────────────────────────

def format_song_tags(song: Song) -> str:
    """Collect event + mood + genre tags into a sorted, deduplicated string."""
    tags: list[str] = []
    tags.extend(split_tags(song.get("event", "")))
    tags.extend(split_tags(song.get("mood", "")))
    tags.extend(split_tags(song.get("genre", "")))
    return ", ".join(sorted({tag for tag in tags if tag})) or "none"


def build_song_context(matched: list[Song]) -> str:
    """Build structured metadata the LLM can reason over."""
    if not matched:
        return (
            "No strong dataset matches found. Suggest outside songs only if needed, "
            "and clearly label them as outside the dataset."
        )

    lines = ["Available songs from the dataset:"]
    for idx, song in enumerate(matched, start=1):
        title = song.get("song", "Unknown")
        energy = song.get("energy", "N/A")
        bpm = song.get("bpm", "Unknown")
        genres = ", ".join(split_tags(song.get("genre", ""))) or "unknown"
        tags = format_song_tags(song)

        lines.append(f"{idx}. {title}")
        lines.append(f"   Energy: {energy}/10")
        lines.append(f"   BPM: {bpm}")
        lines.append(f"   Genres: {genres}")
        lines.append(f"   Tags: {tags}")

    return "\n".join(lines)


def format_song_list(matched: list[Song]) -> str:
    """Format matched songs as a numbered list for the terminal."""
    if not matched:
        return "No strong dataset matches found yet."

    lines = ["Matched Songs:"]
    for index, song in enumerate(matched, start=1):
        details = [
            f"energy {song.get('energy', '?')}/10",
            song.get("genre", "unknown genre"),
        ]
        if song.get("moment"):
            details.append(song["moment"])
        lines.append(f"{index}. {song['song']} ({'; '.join(details)})")
    return "\n".join(lines)


# ── Prompt assembly ───────────────────────────────────────────────────────────

def build_prompt(request: dict, matched: list[Song]) -> str:
    """Fill the prompt template with the current request and matched songs."""
    return BASE_PROMPT.format(
        event=request["event"],
        mood=request["mood"],
        region=request["region"] or "not specified",
        crowd=request["crowd"] or "mixed Indian wedding crowd",
        songs=build_song_context(matched),
    )


# ── LLM call ──────────────────────────────────────────────────────────────────

def generate_playlist(final_prompt: str) -> str:
    """Send *final_prompt* to the local Ollama API and return the response text."""
    payload = json.dumps(
        {"model": MODEL, "prompt": final_prompt, "stream": False},
    ).encode("utf-8")

    ollama_request = request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(ollama_request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(
            "Could not reach Ollama. Start it with `ollama run phi3`, "
            "then run this app in another terminal."
        ) from exc

    return json.loads(body).get("response", "").strip()
