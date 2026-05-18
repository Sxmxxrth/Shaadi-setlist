# Goal Description

The current architecture of ShaadiSetlist relies on a static `dataset.json` (~150 manually curated songs). This guarantees high-quality metadata (energy, tags, BPM) but becomes stale quickly as new trending songs are released. 

The goal is to introduce an automated mechanism to fetch and integrate the latest wedding songs without losing the rich metadata that makes the AI DJ prompt work well.

## User Review Required

Please review the following three architectural options for solving this problem. Once you decide which approach fits your vision best, I will begin implementing it.

### Option 1: Live Spotify API Integration (Recommended)
We integrate the Spotify Web API to dynamically search for live playlists (e.g., "Trending Sangeet 2026", "New Punjabi Wedding Songs").
- **How it works:** When a user queries `sangeet, hype`, we query Spotify for relevant playlists, extract the top tracks, and use Spotify's built-in "Audio Features" API to get actual `energy`, `tempo` (BPM), and `danceability` scores. We combine these live results with our local dataset.
- **Pros:** Always up-to-date. Extremely accurate, mathematically calculated energy and BPM data straight from Spotify.
- **Cons:** Requires internet access during the search phase. Requires setting up Spotify Developer credentials (Client ID and Secret) in the `.env` file. Spotify doesn't provide "baraat" or "gen-z" tags natively, so we'd map genres or rely on the LLM to interpret the titles.

### Option 2: The Hybrid "Auto-Updater" Pipeline
We keep the local `dataset.json` as the source of truth, but we build a script (`src/update_dataset.py`) that runs in the background or on command to fetch new songs and auto-tag them.
- **How it works:** The script scrapes top charts (from YouTube or Spotify), then passes the raw song titles to a fast LLM (like Gemini or Claude) with a prompt like: *"Here are 50 trending Indian songs. Tag them with our internal metadata schema: event (baraat/sangeet), mood, energy (1-10), region."* The results are permanently saved to `dataset.json`.
- **Pros:** Retrieval remains instant and offline. The LLM handles the complex tagging (mapping new songs to "gen-z" or "haldi"), keeping our data schema clean.
- **Cons:** Requires a cloud LLM API key (like Gemini or OpenAI) for the updater script, because local LLMs (like `phi3`) might struggle to batch-tag 50 songs reliably without hallucinating JSON formats. 

### Option 3: Live YouTube Search via `yt-dlp`
Since we already use `yt-dlp` for downloading MP3s, we can use its search capabilities to find songs on the fly.
- **How it works:** User asks for `baraat, hype`. We instantly run a silent `yt-dlp` search for `"ytsearch15: latest baraat hype dance songs"` and extract the titles. We feed those titles directly to the local LLM to build the playlist.
- **Pros:** Zero new dependencies. No API keys needed. Completely free.
- **Cons:** Extremely poor metadata. We won't know the energy level, the BPM, or the exact genre. The local AI DJ will have to guess the vibe of the song based purely on the YouTube video title, which often leads to poor transitions and inaccurate DJ reasoning.

## Open Questions

> [!IMPORTANT]
> **Which option do you prefer?**
> 1. Live Spotify API (Requires Spotify API keys, best metadata)
> 2. Hybrid Auto-Updater (Maintains local dataset, uses an LLM to auto-tag new songs)
> 3. Live YouTube Search (No API keys needed, but very poor metadata)

> [!NOTE]
> If you choose Option 1, are you comfortable registering a free Spotify Developer app to get the API keys?

## Proposed Changes (Example for Option 1 - Spotify)

If we go with the Spotify route, here is what would change:

### src
#### [NEW] [spotify.py](file:///absolute/path/to/new/spotify.py)
A new module to handle Spotify authentication and API requests. Will contain functions to search playlists and fetch audio features (energy/bpm).

#### [MODIFY] [retrieval.py](file:///absolute/path/to/modified/retrieval.py)
Update `filter_songs()` to asynchronously fetch top tracks from Spotify and merge them with the local `dataset.json` matches, normalizing Spotify's 0.0-1.0 energy scale to our 1-10 scale.

#### [MODIFY] [config.py](file:///absolute/path/to/modified/config.py)
Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` environment variables.

### root
#### [MODIFY] [requirements.txt](file:///absolute/path/to/modified/requirements.txt)
Add `spotipy` or `httpx` for making Spotify API calls.

## Verification Plan

### Automated Tests
- Mock the Spotify API or YouTube search responses to ensure the retrieval pipeline correctly merges live songs with the local dataset.
- Ensure the merged song objects conform to our `Song` TypedDict.

### Manual Verification
- Run a query like `sangeet, hype, 2026` and verify that the output contains songs released recently that are not currently in `dataset.json`.
- Verify the MP3 download still works for the dynamically fetched songs.
