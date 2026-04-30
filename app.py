import requests
import json

API_URL = "http://localhost:11434/api/generate"

# Load dataset
with open("dataset.json") as f:
    songs = json.load(f)

# Load prompt
with open("prompt.txt") as f:
    base_prompt = f.read()

# ── Synonym maps so "hype" matches "high energy" etc. ──────────────────────
EVENT_ALIASES = {
    "mehendi": ["mehendi", "mehndi", "henna"],
    "haldi":   ["haldi", "turmeric"],
    "sangeet": ["sangeet", "sangeeth", "music night"],
    "wedding": ["wedding", "shaadi", "ceremony", "pheras", "baraat"],
    "reception": ["reception", "party"],
    "bidaai":  ["bidaai", "vidaai"],
    "cocktail": ["cocktail", "pre-party", "evening"],
}

MOOD_ALIASES = {
    "high energy": ["high energy", "hype", "energetic", "upbeat", "party", "dance"],
    "romantic":    ["romantic", "love", "couple", "soft", "dreamy"],
    "emotional":   ["emotional", "sad", "teary", "sentimental", "feeling"],
    "fun":         ["fun", "funny", "light", "casual", "playful"],
    "classy":      ["classy", "elegant", "sophisticated", "sufi", "indie"],
}


def normalize(term: str, alias_map: dict) -> str:
    """Return the canonical key if term matches any alias, else return term as-is."""
    term = term.strip().lower()
    for canonical, aliases in alias_map.items():
        if any(term == a or term in a or a in term for a in aliases):
            return canonical
    return term


def filter_songs(event: str, mood: str) -> list[dict]:
    """
    Return up to 15 best-matched songs as full dicts (not just names),
    so the LLM gets rich context to reason from.
    """
    event_norm = normalize(event, EVENT_ALIASES)
    mood_norm  = normalize(mood,  MOOD_ALIASES)

    scored = []
    for s in songs:
        score = 0

        # Event match (2 pts — more important)
        s_events = [e.strip().lower() for e in s.get("event", "").split(",")]
        if event_norm in s_events or event in s_events:
            score += 2
        elif any(event_norm in e or e in event_norm for e in s_events):
            score += 1  # partial match

        # Mood match (2 pts)
        s_moods = [m.strip().lower() for m in s.get("mood", "").split(",")]
        if mood_norm in s_moods or mood in s_moods:
            score += 2
        elif any(mood_norm in m or m in mood_norm for m in s_moods):
            score += 1

        if score > 0:
            scored.append((score, s.get("energy", 5), s))

    # Sort: best score first, then by energy
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [item[2] for item in scored[:15]]


def build_song_context(matched: list[dict]) -> str:
    """Give the LLM structured metadata, not just song names."""
    if not matched:
        return "No exact matches found — use your expertise to suggest appropriate songs."
    lines = ["Relevant songs from the dataset (use these as anchors):"]
    for s in matched:
        lines.append(
            f"  • {s['song']} | Energy: {s.get('energy','?')}/10 "
            f"| Mood: {s.get('mood','?')} | Genre: {s.get('genre','?')}"
        )
    return "\n".join(lines)


print("🎵 ShaadiSetlist AI  (type 'exit' to quit)\n")
print("Format:  event, mood   e.g.  sangeet, high energy\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        break

    try:
        event, mood = [p.strip() for p in user_input.lower().split(",", 1)]
    except ValueError:
        print("⚠️  Format: event, mood   e.g.  sangeet, hype\n")
        continue

    matched = filter_songs(event, mood)
    song_context = build_song_context(matched)

    # ── Build a fresh prompt each turn (no growing history) ────────────────
    final_prompt = (
        f"{base_prompt}\n\n"
        f"=== CURRENT REQUEST ===\n"
        f"Event: {event}\n"
        f"Mood:  {mood}\n\n"
        f"{song_context}\n\n"
        f"Now generate the full structured playlist as instructed above.\n"
        f"Assistant:"
    )

    try:
        response = requests.post(
            API_URL,
            json={"model": "phi3", "prompt": final_prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        reply = response.json().get("response", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"❌ API error: {e}\n")
        continue

    print(f"\n🎧 Playlist:\n{reply}\n")
    print("─" * 60 + "\n")