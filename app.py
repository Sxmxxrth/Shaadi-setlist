import json
import os
import re
from pathlib import Path
from typing import TypedDict
from urllib import error, request

import dotenv

BASE_DIR = Path(__file__).resolve().parent
dotenv.load_dotenv(BASE_DIR / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
API_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL = os.getenv("OLLAMA_MODEL", "phi3")

class Song(TypedDict, total=False):
    song: str
    event: str
    mood: str
    region: str
    language: str
    genre: str
    crowd: str
    energy: float | int
    bpm: str | int | float
    moment: str


# Load dataset
with open(BASE_DIR / "dataset.json") as f:
    songs = json.load(f)

# Load prompt
with open(BASE_DIR / "prompt.txt") as f:
    base_prompt = f.read()

# ── Synonym maps so "hype" matches "high energy" etc. ──────────────────────
EVENT_ALIASES = {
    "mehendi": ["mehendi", "mehndi", "henna"],
    "haldi":   ["haldi", "turmeric"],
    "sangeet": ["sangeet", "sangeeth", "music night"],
    "wedding": ["wedding", "shaadi", "ceremony", "pheras"],
    "baraat": ["baraat", "baaraat", "groom entry", "procession"],
    "reception": ["reception", "party"],
    "bidaai":  ["bidaai", "vidaai"],
    "cocktail": ["cocktail", "pre-party", "evening"],
    "garba": ["garba", "dandiya"],
}

MOOD_ALIASES = {
    "high energy": ["high energy", "hype", "energetic", "upbeat", "party", "dance"],
    "romantic":    ["romantic", "love", "couple", "soft", "dreamy", "slow"],
    "emotional":   ["emotional", "sad", "teary", "sentimental", "feeling"],
    "fun":         ["fun", "funny", "light", "casual", "playful"],
    "classy":      ["classy", "elegant", "sophisticated", "sufi", "indie"],
    "traditional": ["traditional", "folk", "ritual", "family"],
    "spiritual":   ["spiritual", "devotional", "sufi", "qawwali"],
}

REGION_ALIASES = {
    "punjabi": ["punjabi", "punjab"],
    "bhangra": ["bhangra"],
    "gujarati": ["gujarati", "gujarat", "garba", "dandiya"],
    "marathi": ["marathi", "maharashtrian", "maharashtra"],
    "haryanvi": ["haryanvi", "haryana"],
    "north indian": ["north indian", "north india"],
    "south indian": ["south indian", "tamil", "telugu", "kannada", "malayalam"],
    "bhojpuri": ["bhojpuri"],
    "bengali": ["bengali", "bangla"],
    "rajasthani": ["rajasthani", "rajasthan"],
    "bollywood": ["bollywood", "hindi"],
}

CROWD_ALIASES = {
    "family": ["family", "parents", "relatives"],
    "gen-z": ["gen-z", "gen z", "genz", "young", "friends"],
    "elders": ["elders", "older", "senior"],
    "mixed": ["mixed", "everyone", "all ages"],
}


def normalize(term: str, alias_map: dict) -> str:
    """Return the canonical key if term matches any alias, else return term as-is."""
    term = term.strip().lower()
    for canonical, aliases in alias_map.items():
        if any(term == a or term in a or a in term for a in aliases):
            return canonical
    return term


def split_tags(value: str) -> list[str]:
    return [item.strip().lower() for item in str(value or "").split(",") if item.strip()]


def match_tag(term: str, tags: list[str], alias_map: dict) -> tuple[bool, bool]:
    """Return (exact_match, partial_match) after applying aliases to both sides."""
    term_norm = normalize(term, alias_map)
    tag_norms = [normalize(tag, alias_map) for tag in tags]
    exact = term_norm in tag_norms
    partial = any(term_norm in tag or tag in term_norm for tag in tag_norms)
    return exact, partial


def energy_fit(energy: int | float, mood: str) -> float:
    if mood == "emotional":
        return 10 - abs(float(energy) - 3)
    if mood in {"romantic", "classy"}:
        return 10 - abs(float(energy) - 5)
    return float(energy)


def parse_request(user_input: str) -> dict:
    """
    Accept:
      event, mood
      event, mood, region
      event, mood, region, crowd
    Optional values can also be written as region=punjabi or crowd=family.
    """
    text = user_input.strip().lower()
    parts = [p.strip() for p in text.split(",") if p.strip()]

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


def filter_songs(event: str, mood: str, region: str | None = None, crowd: str | None = None) -> list[Song]:
    """
    Return up to 15 best-matched songs as full dicts (not just names),
    so the LLM gets rich context to reason from.
    """
    event_norm = normalize(event, EVENT_ALIASES)
    mood_norm  = normalize(mood,  MOOD_ALIASES)
    region_norm = normalize(region, REGION_ALIASES) if region else None
    crowd_norm = normalize(crowd, CROWD_ALIASES) if crowd else None

    scored = []
    for s in songs:
        score = 0

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
            crowd_exact, crowd_partial = match_tag(crowd_norm, split_tags(s.get("crowd", "")), CROWD_ALIASES)
            if crowd_exact:
                score += 1
            elif crowd_partial:
                score += 0.5

        if score > 0:
            both_match = int(event_exact and mood_exact)
            scored.append((both_match, score, energy_fit(s.get("energy", 5), mood_norm), s))

    # Sort: exact event+mood first, then strongest score, then energy.
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [item[3] for item in scored[:15]]


def format_song_tags(song: Song) -> str:
    tags = []
    tags.extend(split_tags(song.get("event", "")))
    tags.extend(split_tags(song.get("mood", "")))
    tags.extend(split_tags(song.get("genre", "")))
    return ", ".join(sorted({tag for tag in tags if tag})) or "none"


def build_song_context(matched: list[Song]) -> str:
    """Give the LLM structured metadata using the user prompt format."""
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


def build_prompt(request: dict, matched: list[Song]) -> str:
    event = request["event"]
    mood = request["mood"]
    region = request["region"] or "not specified"
    crowd = request["crowd"] or "mixed Indian wedding crowd"
    song_context = build_song_context(matched)

    # Build a fresh prompt each turn so prior requests do not pollute the answer.
    return base_prompt.format(
        event=event,
        mood=mood,
        region=region,
        crowd=crowd,
        songs=song_context,
    )


def generate_playlist(final_prompt: str) -> str:
    payload = json.dumps({"model": MODEL, "prompt": final_prompt, "stream": False}).encode("utf-8")
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
            "Could not reach Ollama. Start it with `ollama run phi3`, then run this app in another terminal."
        ) from exc

    return json.loads(body).get("response", "").strip()


def looks_like_shell_command(user_input: str) -> bool:
    commands = ("python ", "python3 ", "pip ", "pip3 ", "ollama ", "brew ", "npm ", "git ", "yt-dlp ")
    return user_input.strip().lower().startswith(commands)





def main() -> None:
    print("🎵 ShaadiSetlist AI  (type 'exit' to quit)\n")
    print("Format:  event, mood[, region][, crowd]   e.g.  sangeet, high energy, punjabi, gen-z")
    print("Also works without commas: shaadi slow\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            break

        if looks_like_shell_command(user_input):
            print("That looks like a terminal command. Type `exit`, run it in your shell, then start the app again.\n")
            continue

        try:
            request = parse_request(user_input)
        except ValueError:
            print("⚠️  Format: event, mood[, region][, crowd]   e.g.  sangeet, hype, punjabi, family\n")
            continue

        matched = filter_songs(
            request["event"],
            request["mood"],
            region=request["region"],
            crowd=request["crowd"],
        )
        print(f"\n{format_song_list(matched)}\n")
        
        # Ask if user wants to download matched songs
        if matched:
            matched_names = [s["song"] for s in matched]
            choice = input(f"Download these {len(matched_names)} matched songs as MP3? (y/n): ").strip().lower()
            if choice == 'y':
                from download_songs import download_songs
                download_songs(matched_names)
                print()
        
        final_prompt = build_prompt(request, matched)

        try:
            reply = generate_playlist(final_prompt)
        except Exception as e:
            print(f"AI playlist unavailable: {e}\n")
            # Offer to download matched songs even without the LLM
            if matched:
                matched_names = [s["song"] for s in matched]
                choice = input(f"Download these {len(matched_names)} matched songs as MP3? (y/n): ").strip().lower()
                if choice == 'y':
                    from download_songs import download_songs
                    download_songs(matched_names)
                print("─" * 60 + "\n")
            continue

        print(f"🎧 AI Playlist:\n{reply}\n")
        
        # Extract song names from numbered lines in the LLM output
        raw_matches = [name.strip() for name in re.findall(r"^\d+\.\s+([^\n]+)", reply, re.MULTILINE) if name.strip()]
        # Strip markdown bold (**), LLM prefixes like "Song Name:", and trailing annotations
        cleaned = []
        for m in raw_matches:
            m = m.strip().strip("*").strip()                                        # remove **bold**
            m = re.sub(r"^(?:Song\s*Name\s*:\s*|Song\s*:\s*)", "", m, flags=re.IGNORECASE).strip()
            m = re.sub(r"\s*\(.*$", "", m).strip()                                  # remove (Repeated), (energy 9/10), etc.
            m = re.sub(r"\s*[\-–—]\s+\S.*$", "", m).strip()                         # remove " - As we kick off..."
            m = m.strip("* ").strip()                                               # final cleanup of any remaining markdown
            if m:
                cleaned.append(m)
        # Cross-reference against dataset to drop hallucinated songs
        dataset_titles = {s["song"].strip().lower() for s in songs}
        verified = list(dict.fromkeys(name for name in cleaned if name.strip().lower() in dataset_titles))

        if verified:
            print(f"Found {len(verified)} downloadable songs in the playlist:")
            for i, name in enumerate(verified, 1):
                print(f"  {i}. {name}")
            if len(verified) < len(cleaned):
                skipped = [n for n in cleaned if n.strip().lower() not in dataset_titles]
                print(f"  (skipped {len(skipped)} song(s) not in dataset: {', '.join(skipped)})")
                
            choice = input(f"\nDownload these as MP3? (y/n): ").strip().lower()
            if choice == 'y':
                from download_songs import download_songs
                download_songs(verified)

        print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
