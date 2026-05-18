# ShaadiSetlist

AI-assisted Indian wedding playlist curator.

The app uses a maintained song dataset for retrieval, then asks a local Ollama model to turn matched songs into a practical event playlist. After generating a playlist, it can automatically download the songs as MP3 via yt-dlp.

## Project Structure

```
shaadi-setlist/
├── main.py                  # Entry point
├── src/
│   ├── config.py            # Paths, env vars, dataset & prompt loading
│   ├── models.py            # Song TypedDict
│   ├── aliases.py           # Synonym maps & tag helpers
│   ├── retrieval.py         # Request parsing & song matching
│   ├── playlist.py          # LLM prompt building & generation
│   ├── app.py               # Interactive CLI loop
│   ├── mashup_planner.py    # DJ-ready song ordering & transitions
│   ├── audio_mashup.py      # ffmpeg command builder for audio mashups
│   └── download_songs.py    # yt-dlp MP3 downloader
├── data/
│   ├── dataset.json         # Song database (source of truth)
│   ├── prompt.txt           # LLM prompt template
│   └── audio_manifest.example.json
├── tests/
│   ├── conftest.py          # Pytest config
│   ├── test_retrieval.py    # Retrieval accuracy tests
│   ├── test_mashup.py       # Mashup planner tests
│   ├── test_audio_mashup.py # Audio command builder tests
│   └── eval_cases.json      # Test fixtures
└── DATASET_GUIDE.md         # Schema & expansion guide
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You also need [Ollama](https://ollama.com) running locally and [ffmpeg](https://ffmpeg.org) installed for audio features:

```bash
# macOS
brew install ffmpeg

# Start the LLM
ollama run phi3
```

### Configuration

Copy or edit the `.env` file in the project root:

```env
OLLAMA_MODEL=phi3
OLLAMA_BASE_URL=http://localhost:11434
```

These are read automatically at startup — no need to pass flags.

Optional environment variables:

```env
ENABLE_LIVE_YOUTUBE_SEARCH=false
LIVE_SEARCH_LIMIT=8
```

If `ENABLE_LIVE_YOUTUBE_SEARCH` is enabled and the local dataset has no strong matches, ShaadiSetlist will perform a lightweight YouTube search fallback to suggest recent wedding song candidates.

You can also enable it when starting the app:

```bash
python main.py --enable-live-search
```

## Run

```bash
source venv/bin/activate
python3 main.py
```

### Gradio UI

Launch the browser interface:

```bash
source venv/bin/activate
python3 main.py --ui
```

The UI has two tabs:

- Playlist Curator: finds matching songs and asks Ollama to arrange them.
- Mashup Planner: creates a DJ-ready song order and transition plan.

### One-command Demo Workflow

Run setup checks, validate the dataset, execute tests, check Ollama, and launch the UI:

```bash
source venv/bin/activate
python3 main.py --workflow
```

To run the same checks without launching the UI:

```bash
python3 main.py --workflow-check
```

If Ollama is not running, the workflow prints:

```bash
ollama run phi3
```

Input format:

```text
event, mood[, region][, crowd]
```

Examples:

```text
sangeet, high energy
shaadi slow
haldi, fun, family
cocktail, classy, gen-z
baraat, hype, punjabi
```

After the AI generates a playlist, the app will ask if you want to download the songs as MP3. It cross-references the LLM output against the dataset to skip hallucinated titles.

## Song Downloader

Download songs as MP3 via YouTube search using yt-dlp:

```bash
# Standalone (uses a built-in demo list)
python3 -m src.download_songs

# Or triggered automatically from the CLI after playlist generation
```

Songs are saved to `downloads/` at 192kbps MP3. Failed downloads are skipped gracefully with a summary at the end.

## Data

Maintain `dataset.json` as the source of truth. See `DATASET_GUIDE.md` for the recommended schema and expansion priorities.

## Retrieval and RAG

ShaadiSetlist uses two local retrieval layers:

1. Rule-based scoring for event, mood, region, crowd, and energy fit.
2. Lightweight local RAG over dataset metadata such as title, event, mood, genre, region, language, crowd, moment, and notes.

No vector database is required for the local demo. The RAG index is built in memory at startup and helps the LLM receive the most relevant local song metadata before it generates the playlist.

Fine-tuning is future work. The current dataset is useful for retrieval, but fine-tuning should wait until there are enough high-quality examples of user requests, retrieved songs, ideal playlists, and DJ reasoning.

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Mashup Planning

Generate a DJ-ready song order and transition plan:

```bash
python3 -m src.mashup_planner "baraat, hype, punjabi, gen-z"
python3 -m src.mashup_planner "haldi, fun, family" --length 6
```

This does not merge audio yet. It plans the flow, energy curve, and transition ideas. Real audio mashups will need additional metadata like `bpm`, `key`, `hook_start`, `hook_end`, and local audio files.

## Audio Mashup Command

Create a local manifest from the example:

```bash
cp data/audio_manifest.example.json data/audio_manifest.local.json
```

Update `audio_manifest.local.json` with your local audio file paths and hook timings, then dry-run an ffmpeg command:

```bash
python3 -m src.audio_mashup "baraat, hype, punjabi, gen-z" --length 5
```

When the manifest points to real audio files and `ffmpeg` is installed:

```bash
python3 -m src.audio_mashup "baraat, hype, punjabi, gen-z" --length 5 --execute
```

Local audio files, output files, downloads, and `audio_manifest.local.json` are ignored by git.
