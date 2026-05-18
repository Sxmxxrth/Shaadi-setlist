"""
mashup_planner — Create a DJ-ready song order and transition plan.

Given a user query, this module retrieves matching songs, orders them into
an energy-aware flow, and generates transition recommendations between
consecutive tracks.

CLI usage::

    python -m src.mashup_planner "baraat, hype, punjabi, gen-z"
    python -m src.mashup_planner "haldi, fun, family" --length 6
"""

import argparse

from src.aliases import MOOD_ALIASES, normalize, split_tags
from src.models import Song
from src.retrieval import filter_songs, parse_request

DEFAULT_LENGTH = 8


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_energy(song: Song) -> int:
    """Return a song's energy level as an integer (default 5)."""
    return int(song.get("energy", 5))


def get_tags(song: Song, field: str) -> set[str]:
    """Return the set of tags for a given metadata field."""
    return set(split_tags(song.get(field, "")))


def get_region_tags(song: Song) -> set[str]:
    """Combine region, language, and genre tags into one set."""
    return get_tags(song, "region") | get_tags(song, "language") | get_tags(song, "genre")


# ── Transitions ───────────────────────────────────────────────────────────────

def transition_style(current: Song, next_song: Song) -> str:
    """Suggest a DJ transition technique between two consecutive songs."""
    energy_a = get_energy(current)
    energy_b = get_energy(next_song)
    shared_region = get_region_tags(current) & get_region_tags(next_song)
    shared_mood = get_tags(current, "mood") & get_tags(next_song, "mood")

    if energy_b - energy_a >= 2:
        return "Build with an 8-count loop, then cut into the next hook/drop."
    if energy_a - energy_b >= 2:
        return "Use a short echo-out or crowd chant before lowering the energy."
    if shared_region and shared_mood:
        return "Blend over a shared percussion groove for a smooth style match."
    if shared_region:
        return "Keep the regional groove consistent and switch at the chorus."
    if shared_mood:
        return "Use a quick hook-to-hook cut; the mood will carry the transition."
    return "Use a clean 4-count cut and let the next song reset the vibe."


def transition_reason(current: Song, next_song: Song) -> str:
    """Explain *why* two songs sit next to each other in the plan."""
    energy_a = get_energy(current)
    energy_b = get_energy(next_song)
    shared = sorted(
        (get_region_tags(current) & get_region_tags(next_song))
        | (get_tags(current, "mood") & get_tags(next_song, "mood"))
    )

    if shared:
        return f"Shared tags: {', '.join(shared[:3])}; energy {energy_a} -> {energy_b}."
    return f"Energy moves {energy_a} -> {energy_b}, giving the set a clear shift."


# ── Ordering ──────────────────────────────────────────────────────────────────

def order_for_mashup(songs: list[Song], mood: str, length: int = DEFAULT_LENGTH) -> list[Song]:
    """
    Sort *songs* into a DJ-friendly order based on the requested *mood*.

    Soft moods get a gentle ascending sort.  High-energy moods get a
    warmup → middle → peak arc.
    """
    selected = songs[:length]
    mood_norm = normalize(mood, MOOD_ALIASES)

    if mood_norm in {"emotional", "romantic", "classy"}:
        return sorted(selected, key=lambda song: (get_energy(song), song.get("song", "")))

    if len(selected) <= 3:
        return sorted(selected, key=get_energy)

    ordered = sorted(selected, key=get_energy)
    if len(ordered) == 4:
        return ordered

    warmup = ordered[:2]
    peak = ordered[-3:]
    middle = ordered[2:-3]
    return warmup + middle + peak


# ── Plan building ─────────────────────────────────────────────────────────────

def build_mashup_plan(user_input: str, length: int = DEFAULT_LENGTH) -> dict:
    """Build a complete mashup plan from a user query string."""
    request = parse_request(user_input)
    matched = filter_songs(
        request["event"],
        request["mood"],
        region=request["region"],
        crowd=request["crowd"],
    )
    ordered = order_for_mashup(matched, request["mood"], length=length)

    transitions = []
    for index in range(len(ordered) - 1):
        current = ordered[index]
        next_song = ordered[index + 1]
        transitions.append({
            "from": current["song"],
            "to": next_song["song"],
            "style": transition_style(current, next_song),
            "reason": transition_reason(current, next_song),
        })

    return {
        "request": request,
        "songs": ordered,
        "transitions": transitions,
    }


# ── Formatting ────────────────────────────────────────────────────────────────

def format_plan(plan: dict) -> str:
    """Render a mashup plan as a human-readable string."""
    request = plan["request"]
    songs = plan["songs"]
    transitions = plan["transitions"]

    lines = [
        "Mashup Playlist Plan",
        f"Event: {request['event']}",
        f"Mood: {request['mood']}",
        f"Region: {request['region'] or 'not specified'}",
        f"Crowd: {request['crowd'] or 'mixed'}",
        "",
        "Song Flow:",
    ]

    for index, song in enumerate(songs, start=1):
        details = [
            f"energy {song.get('energy', '?')}/10",
            song.get("genre", "unknown genre"),
        ]
        if song.get("moment"):
            details.append(song["moment"])
        lines.append(f"{index}. {song['song']} ({'; '.join(details)})")

    lines.append("")
    lines.append("Transitions:")
    for index, transition in enumerate(transitions, start=1):
        lines.append(f"{index}. {transition['from']} -> {transition['to']}")
        lines.append(f"   {transition['style']}")
        lines.append(f"   {transition['reason']}")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    """CLI entry point for standalone mashup planning."""
    parser = argparse.ArgumentParser(description="Create a DJ-ready mashup playlist plan.")
    parser.add_argument("request", help="Example: 'baraat, hype, punjabi, gen-z'")
    parser.add_argument("--length", type=int, default=DEFAULT_LENGTH, help="Number of songs to include")
    args = parser.parse_args()

    plan = build_mashup_plan(args.request, length=args.length)
    print(format_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
