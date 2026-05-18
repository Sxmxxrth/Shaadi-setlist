# ShaadiSetlist Workflow — Issues Analysis

After cross-referencing [project_workflow.md](file:///Users/samarth/Downloads/project_workflow.md) against every source file, here's what I found. All 11 tests pass, so the core logic works — but there are real problems.

---

## 🔴 Critical Issues (Bugs / Broken Behavior)

### 1. `normalize()` has a dangerously loose matching function

**File:** [aliases.py:63](file:///Users/samarth/Desktop/shaadi-setlist/src/aliases.py#L63)

```python
if any(term == a or term in a or a in term for a in aliases):
```

The `term in a or a in term` substring checks cause **false positives**. For example:
- `"fun"` matches `"funny"` ✅ (intended) — but also matches `"s**fun**k"` or any string containing `"fun"`
- `"party"` (a mood alias for `high energy`) **collides** with `"pre-party"` (an event alias for `cocktail`)
- `"folk"` (mood: traditional) would match `"folk**lore**"` or `"norfolk"`
- `"sad"` would match inside any alias containing "sad" as a substring

This means a user typing `"party"` as an event could silently get mis-normalized to a mood instead, producing wrong results. The workflow document doesn't mention this fragility at all.

### 2. Double download prompt — broken UX flow

**File:** [app.py:120-149](file:///Users/samarth/Desktop/shaadi-setlist/src/app.py#L120-L149)

The main loop offers download **twice**:
1. **Line 122**: Downloads the raw `filter_songs()` matches *before* calling the LLM
2. **Line 146-149**: Downloads the LLM's verified playlist *after* generation

If the user says "yes" to the first prompt, they download 15 raw matches, then *still* get prompted again for the AI-curated subset. This is confusing and could lead to downloading duplicates. The workflow document (Step 6) only describes the second download, hiding this double-prompt from the reader.

### 3. `requests` library is not in `requirements.txt` but `python-dotenv` import is named `dotenv`

**File:** [requirements.txt](file:///Users/samarth/Desktop/shaadi-setlist/requirements.txt)

```
python-dotenv
pytest
yt-dlp
```

While `python-dotenv` imports as `dotenv` (which is correct), the **`requests`** library is conspicuously absent — but that's actually fine because the code uses `urllib` instead. However, `shutil`, `subprocess`, `argparse`, `json`, `re`, `pathlib` are all stdlib. No issues there.

> [!WARNING]
> The real problem: if someone installs from `requirements.txt` on a fresh machine, there's no `ffmpeg` system dependency documented as required. The workflow mentions it in the download_songs docstring but `requirements.txt` doesn't flag it and there's no setup script.

---

## 🟡 Documentation Inaccuracies (Workflow ≠ Code)

### 4. Workflow says `parse_request()` normalizes inputs — it doesn't

The workflow (Step 1) says `parse_request()` produces normalized output like `"event": "sangeet"`. In reality, [parse_request()](file:///Users/samarth/Desktop/shaadi-setlist/src/retrieval.py#L24-L70) stores the **raw tokens** (`parts[0]`, `parts[1]`) without normalization. Normalization happens later inside `filter_songs()` (line 96-99). This is a meaningful distinction — the `request` dict flowing through the system contains un-normalized values.

### 5. Workflow claims the dataset has "~150 songs" — verify this

The workflow repeatedly says "~150 songs." The dataset file is 45KB which is plausible, but the workflow should be specific rather than approximate, especially since the scoring weights were tuned for this size.

### 6. `models.py` — Song TypedDict is missing `notes` and `danceability` fields

**File:** [models.py](file:///Users/samarth/Desktop/shaadi-setlist/src/models.py)

The workflow (Data Layer section) shows `dataset.json` entries having `notes` and `danceability` fields, and the example JSON confirms this. But the `Song` TypedDict doesn't declare them:

```python
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
    # missing: notes, danceability
```

Since `total=False` makes all fields optional and the code uses `.get()` everywhere, this doesn't crash — but it defeats the purpose of having a TypedDict for type safety. Any code accessing `song["danceability"]` won't get type-checker coverage.

### 7. Architecture diagram shows `build_mashup_plan()` feeding from the **Top 15** songs, but the code uses a separate `parse_request()` call

The mermaid diagram in the workflow shows a single `filter_songs()` result (node F) feeding **both** the playlist pipeline and the mashup pipeline. In reality, `build_mashup_plan()` calls `parse_request()` and `filter_songs()` independently — it doesn't share results with the playlist flow. This is a minor doc inaccuracy but could confuse a contributor.

---

## 🟠 Architectural Concerns

### 8. `app.py` re-exports everything — defeats the purpose of modularization

**File:** [app.py:27-37](file:///Users/samarth/Desktop/shaadi-setlist/src/app.py#L27-L37)

```python
from src.aliases import (  # noqa: F401
    CROWD_ALIASES, EVENT_ALIASES, MOOD_ALIASES, REGION_ALIASES,
    match_tag, normalize, split_tags,
)
from src.models import Song  # noqa: F401
from src.retrieval import energy_fit  # noqa: F401
```

The comment says "backward-compatible re-exports" for `mashup_planner.py` — but `mashup_planner.py` actually imports directly from `src.aliases`, `src.models`, and `src.retrieval`. **No module imports these from `app.py` anymore.** These re-exports are dead code that creates a false dependency and makes the module graph messier than the workflow's dependency diagram suggests.

### 9. `config.py` loads dataset and prompt at **import time** — side effects on import

**File:** [config.py:28-32](file:///Users/samarth/Desktop/shaadi-setlist/src/config.py#L28-L32)

```python
with open(PROJECT_ROOT / "data" / "dataset.json") as _f:
    SONGS: list[dict] = json.load(_f)

with open(PROJECT_ROOT / "data" / "prompt.txt") as _f:
    BASE_PROMPT: str = _f.read()
```

This means importing *anything* from `config` triggers file I/O. If `dataset.json` or `prompt.txt` is missing/corrupt, you get an unhandled crash at import time with no clear error message. The workflow doesn't mention this risk.

### 10. No error handling in `parse_request()` for the auto-detect logic

**File:** [retrieval.py:62-68](file:///Users/samarth/Desktop/shaadi-setlist/src/retrieval.py#L62-L68)

When the 3rd/4th tokens aren't recognized as either a region or a crowd, they're **silently dropped**. The user gets no feedback that part of their input was ignored. For example: `"sangeet, hype, xyz"` — `xyz` vanishes without a trace.

### 11. LLM timeout is hardcoded to 120 seconds with no retry

**File:** [playlist.py:98](file:///Users/samarth/Desktop/shaadi-setlist/src/playlist.py#L98)

```python
with request.urlopen(ollama_request, timeout=120) as response:
```

Local LLMs like `phi3` can be slow on CPU. 120s may not be enough for longer playlists, and there's zero retry logic. If Ollama is booting up, the first request will always fail.

---

## 🔵 Minor Nits

| # | Issue | Location |
|---|---|---|
| 12 | Workflow example manifest JSON (line 265-273) doesn't show the `"songs"` wrapper key that the actual file has | Workflow line 265 vs [audio_manifest.example.json](file:///Users/samarth/Desktop/shaadi-setlist/data/audio_manifest.example.json) |
| 13 | `download_songs.py` docstring says `python download_songs.py` (standalone) but it lives inside `src/` so it must be `python -m src.download_songs` | [download_songs.py:7](file:///Users/samarth/Desktop/shaadi-setlist/src/download_songs.py#L7) |
| 14 | `SEARCH_SUFFIX = "song official audio"` is naive — Bollywood songs often have better results with "full song" or "audio jukebox" | [download_songs.py:26](file:///Users/samarth/Desktop/shaadi-setlist/src/download_songs.py#L26) |
| 15 | `prompt.txt` line 10-11 hardcodes "Punjabi wedding culture" and "Gen-Z crowd psychology" even for non-Punjabi/elder queries — biases the LLM | [prompt.txt:9-11](file:///Users/samarth/Desktop/shaadi-setlist/data/prompt.txt#L9-L11) |
| 16 | No `.gitignore` entry for `data/audio_manifest.local.json` (the user's private manifest) — risk of accidentally committing local audio paths | [.gitignore](file:///Users/samarth/Desktop/shaadi-setlist/.gitignore) |

---

## ✅ What's Working Well

- All **11 tests pass** cleanly
- The scoring system in `filter_songs()` is well-designed with sensible weights
- The mashup planner's energy-arc ordering is clever (warmup → middle → peak)
- The ffmpeg command builder is thorough with proper fade-in/fade-out
- The `_extract_verified_songs()` regex cleanup is robust against common LLM output quirks
- Module separation is clean (despite the dead re-exports in app.py)
