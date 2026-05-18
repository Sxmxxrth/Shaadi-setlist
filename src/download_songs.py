"""
download_songs.py  —  ShaadiSetlist Song Downloader
----------------------------------------------------
Uses yt-dlp to search YouTube and download matched songs as MP3.

Usage (standalone):
    python download_songs.py

Or import and call download_songs(song_list) from your app.py.

Requirements:
    pip install yt-dlp
    # ffmpeg must also be installed for audio conversion:
    # macOS:  brew install ffmpeg
    # Ubuntu: sudo apt install ffmpeg
"""

import subprocess
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "downloads"
AUDIO_QUALITY = "192"                   # kbps  (128 / 192 / 320)
SEARCH_SUFFIX = "song official audio"   # appended to each search query

# ── Helpers ───────────────────────────────────────────────────────────────────


def ensure_yt_dlp():
    """Check yt-dlp is importable; prompt to install if not."""
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print("⚠️  yt-dlp not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        print("✅  yt-dlp installed.\n")


def download_songs(songs: list[str], output_dir: Path = OUTPUT_DIR):
    """
    Download a list of song names as MP3 files via YouTube search.

    Args:
        songs:      list of song name strings, e.g. ["Kala Chashma", "London Thumakda"]
        output_dir: Path to save MP3 files
    """
    import yt_dlp

    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": AUDIO_QUALITY,
            }
        ],
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": True,       # skip a song if it fails, don't abort
        "noplaylist": True,
    }

    total = len(songs)
    failed = []

    print(f"\n📁 Saving to: {output_dir.resolve()}")
    print(f"🎵 Downloading {total} songs at {AUDIO_QUALITY}kbps MP3\n")
    print("─" * 50)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, song in enumerate(songs, 1):
            query = f"ytsearch1:{song} {SEARCH_SUFFIX}"
            print(f"[{idx}/{total}]  🔍  {song}")
            try:
                ydl.download([query])
            except Exception as e:
                print(f"       ❌  Failed: {e}")
                failed.append(song)

    print("\n" + "─" * 50)
    print(f"✅  Done! {total - len(failed)}/{total} songs downloaded → {output_dir.resolve()}")

    if failed:
        print(f"\n⚠️  {len(failed)} song(s) failed:")
        for s in failed:
            print(f"   • {s}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_yt_dlp()

    # Default demo list — paste your ShaadiSetlist output here
    MATCHED_SONGS = [
        "Kala Chashma",
        "Gallan Goodiyaan",
        "Nachde Ne Saare",
        "Kar Gayi Chull",
        "Tere Naal Nachna",
        "Mundian To Bach Ke",
        "Shera Di Kaum",
        "Mauja Hi Mauja",
        "London Thumakda",
        "Badri Ki Dulhania",
        "Gur Naal Ishq Mitha",
        "Morni Banke",
        "Makhna",
        "Tareefan",
        "Nagada Sang Dhol",
    ]

    download_songs(MATCHED_SONGS)
