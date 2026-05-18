"""
audio_mashup — Build an ffmpeg command for a hook-based audio mashup.

Takes a mashup plan (from ``mashup_planner``) and a local audio manifest,
resolves hook timings, and generates or executes the ffmpeg filter-complex
command that concatenates the hooks into a single MP3.

CLI usage::

    python -m src.audio_mashup "baraat, hype, punjabi, gen-z" --length 5
    python -m src.audio_mashup "baraat, hype, punjabi, gen-z" --length 5 --execute
"""

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from src import mashup_planner
from src.config import PROJECT_ROOT

DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "audio_manifest.local.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "mashup.mp3"
REQUIRED_FIELDS = ("audio_file", "hook_start", "hook_end")


# ── Time parsing ──────────────────────────────────────────────────────────────

def parse_time(value: str | int | float) -> float:
    """
    Convert a time value to seconds.

    Accepts plain numbers (``42``, ``"42.5"``) or colon-separated formats
    (``"1:23"`` → 83 s, ``"0:01:23"`` → 83 s).
    """
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if ":" not in text:
        return float(text)

    parts = [float(part) for part in text.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported time format: {value}")


# ── Manifest ──────────────────────────────────────────────────────────────────

def load_manifest(path: Path) -> dict:
    """Load the audio manifest JSON and return a title → metadata mapping."""
    with open(path) as f:
        data = json.load(f)
    songs = data.get("songs", data)
    return {title.strip().lower(): metadata for title, metadata in songs.items()}


def resolve_song_metadata(song: dict, manifest: dict) -> tuple[dict | None, list[str]]:
    """Look up a song in the manifest and validate required fields."""
    title = song["song"]
    metadata = manifest.get(title.strip().lower())
    if not metadata:
        return None, [f"{title}: missing from manifest"]

    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        return None, [f"{title}: missing fields: {', '.join(missing)}"]

    try:
        start = parse_time(metadata["hook_start"])
        end = parse_time(metadata["hook_end"])
    except ValueError as exc:
        return None, [f"{title}: {exc}"]

    if end <= start:
        return None, [f"{title}: hook_end must be after hook_start"]

    return {
        "title": title,
        "audio_file": str((PROJECT_ROOT / metadata["audio_file"]).resolve()),
        "start": start,
        "end": end,
        "duration": end - start,
        "bpm": metadata.get("bpm"),
        "key": metadata.get("key"),
    }, []


# ── Clip building ─────────────────────────────────────────────────────────────

def build_clip_specs(plan: dict, manifest: dict) -> tuple[list[dict], list[str]]:
    """Resolve every song in *plan* against *manifest*, collecting clips and errors."""
    clips: list[dict] = []
    errors: list[str] = []

    for song in plan["songs"]:
        clip, clip_errors = resolve_song_metadata(song, manifest)
        errors.extend(clip_errors)
        if clip:
            clips.append(clip)

    return clips, errors


def build_ffmpeg_command(clips: list[dict], output: Path) -> list[str]:
    """Build an ffmpeg command that trims, fades, and concatenates *clips*."""
    if not clips:
        raise ValueError("No clips available to build")

    command = ["ffmpeg", "-y"]

    for clip in clips:
        command.extend(["-i", clip["audio_file"]])

    filters: list[str] = []
    labels: list[str] = []
    for index, clip in enumerate(clips):
        fade_out_start = max(clip["duration"] - 0.6, 0)
        label = f"a{index}"
        filters.append(
            f"[{index}:a]"
            f"atrim=start={clip['start']}:end={clip['end']},"
            "asetpts=PTS-STARTPTS,"
            "afade=t=in:st=0:d=0.2,"
            f"afade=t=out:st={fade_out_start:.3f}:d=0.6"
            f"[{label}]"
        )
        labels.append(f"[{label}]")

    filters.append(f"{''.join(labels)}concat=n={len(clips)}:v=0:a=1[out]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", str(output)])
    return command


# ── Display ───────────────────────────────────────────────────────────────────

def format_command(command: list[str]) -> str:
    """Shell-quote an ffmpeg command for copy-paste."""
    return " ".join(shlex.quote(part) for part in command)


def print_clip_summary(clips: list[dict]) -> None:
    """Print a numbered summary of the clips that will be concatenated."""
    print("Audio Clips:")
    for index, clip in enumerate(clips, start=1):
        bpm = f", bpm {clip['bpm']}" if clip.get("bpm") else ""
        key = f", key {clip['key']}" if clip.get("key") else ""
        print(
            f"{index}. {clip['title']} "
            f"({clip['start']:.1f}s -> {clip['end']:.1f}s, {clip['duration']:.1f}s{bpm}{key})"
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    """CLI entry point for building/running an audio mashup."""
    parser = argparse.ArgumentParser(description="Build an ffmpeg command for a hook-based mashup.")
    parser.add_argument("request", help="Example: 'baraat, hype, punjabi, gen-z'")
    parser.add_argument("--length", type=int, default=mashup_planner.DEFAULT_LENGTH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute", action="store_true", help="Run ffmpeg instead of only printing the command")
    parser.add_argument("--show-plan", action="store_true", help="Print the mashup playlist plan too")
    args = parser.parse_args()

    plan = mashup_planner.build_mashup_plan(args.request, length=args.length)

    if args.show_plan:
        print(mashup_planner.format_plan(plan))
        print()

    if not args.manifest.exists():
        print(f"Missing manifest: {args.manifest}")
        print("Create it from audio_manifest.example.json and point each song to a local audio file.")
        return 1

    manifest = load_manifest(args.manifest)
    clips, errors = build_clip_specs(plan, manifest)
    if errors:
        print("Cannot build audio mashup yet:")
        for error in errors:
            print(f"- {error}")
        return 1

    command = build_ffmpeg_command(clips, args.output)
    print_clip_summary(clips)
    print()
    print("ffmpeg command:")
    print(format_command(command))

    if not args.execute:
        print()
        print("Dry run only. Add --execute to create the audio file after your manifest points to real files.")
        return 0

    if shutil.which("ffmpeg") is None:
        print("ffmpeg is not installed or not on PATH.")
        return 1

    missing_files = [clip["audio_file"] for clip in clips if not Path(clip["audio_file"]).exists()]
    if missing_files:
        print("Missing audio files:")
        for path in missing_files:
            print(f"- {path}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("ffmpeg failed:")
        print(e.stderr)
        return 1
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
