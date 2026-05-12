# ShaadiSetlist

AI-assisted Indian wedding playlist curator.

The app uses a maintained song dataset for retrieval, then asks a local Ollama model to turn matched songs into a practical event playlist. After generating a playlist, it can automatically download the songs as MP3 via yt-dlp.

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

## Run

```bash
source venv/bin/activate
python3 app.py
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
python3 download_songs.py

# Or triggered automatically from app.py after playlist generation
```

Songs are saved to `downloads/` at 192kbps MP3. Failed downloads are skipped gracefully with a summary at the end.

## Data

Maintain `dataset.json` as the source of truth. See `DATASET_GUIDE.md` for the recommended schema and expansion priorities.

## Tests

```bash
source venv/bin/activate
pytest
```

## Mashup Planning

Generate a DJ-ready song order and transition plan:

```bash
python3 mashup_planner.py "baraat, hype, punjabi, gen-z"
python3 mashup_planner.py "haldi, fun, family" --length 6
```

This does not merge audio yet. It plans the flow, energy curve, and transition ideas. Real audio mashups will need additional metadata like `bpm`, `key`, `hook_start`, `hook_end`, and local audio files.

## Audio Mashup Command

Create a local manifest from the example:

```bash
cp audio_manifest.example.json audio_manifest.local.json
```

Update `audio_manifest.local.json` with your local audio file paths and hook timings, then dry-run an ffmpeg command:

```bash
python3 audio_mashup.py "baraat, hype, punjabi, gen-z" --length 5 --manifest audio_manifest.local.json
```

When the manifest points to real audio files and `ffmpeg` is installed:

```bash
python3 audio_mashup.py "baraat, hype, punjabi, gen-z" --length 5 --execute
```

Local audio files, output files, downloads, and `audio_manifest.local.json` are ignored by git.
