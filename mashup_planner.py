import argparse

import app


DEFAULT_LENGTH = 8


def get_energy(song: app.Song) -> int:
    return int(song.get("energy", 5))


def get_tags(song: app.Song, field: str) -> set[str]:
    return set(app.split_tags(song.get(field, "")))


def get_region_tags(song: app.Song) -> set[str]:
    return (
        get_tags(song, "region")
        | get_tags(song, "language")
        | get_tags(song, "genre")
    )


def transition_style(current: app.Song, next_song: app.Song) -> str:
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


def transition_reason(current: app.Song, next_song: app.Song) -> str:
    energy_a = get_energy(current)
    energy_b = get_energy(next_song)
    shared = sorted((get_region_tags(current) & get_region_tags(next_song)) | (get_tags(current, "mood") & get_tags(next_song, "mood")))

    if shared:
        return f"Shared tags: {', '.join(shared[:3])}; energy {energy_a} -> {energy_b}."
    return f"Energy moves {energy_a} -> {energy_b}, giving the set a clear shift."


def order_for_mashup(songs: list[app.Song], mood: str, length: int = DEFAULT_LENGTH) -> list[app.Song]:
    selected = songs[:length]
    mood_norm = app.normalize(mood, app.MOOD_ALIASES)

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


def build_mashup_plan(user_input: str, length: int = DEFAULT_LENGTH) -> dict:
    request = app.parse_request(user_input)
    matched = app.filter_songs(
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
        transitions.append(
            {
                "from": current["song"],
                "to": next_song["song"],
                "style": transition_style(current, next_song),
                "reason": transition_reason(current, next_song),
            }
        )

    return {
        "request": request,
        "songs": ordered,
        "transitions": transitions,
    }


def format_plan(plan: dict) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a DJ-ready mashup playlist plan.")
    parser.add_argument("request", help="Example: 'baraat, hype, punjabi, gen-z'")
    parser.add_argument("--length", type=int, default=DEFAULT_LENGTH, help="Number of songs to include")
    args = parser.parse_args()

    plan = build_mashup_plan(args.request, length=args.length)
    print(format_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
