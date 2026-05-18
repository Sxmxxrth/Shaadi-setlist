"""
app — Interactive CLI for ShaadiSetlist.

The CLI is intentionally thin: shared playlist generation lives in
playlist_service so the terminal and Gradio UI use the same workflow.
"""

import argparse

from src.playlist import format_song_list
from src.playlist_service import (
    extract_verified_songs as _extract_verified_songs,
    generate_playlist_result,
    process_query,
)

# Backward-compatible re-exports for older imports and tests.
from src.aliases import (  # noqa: F401
    CROWD_ALIASES,
    EVENT_ALIASES,
    MOOD_ALIASES,
    REGION_ALIASES,
    match_tag,
    normalize,
    split_tags,
)
from src.models import Song  # noqa: F401
from src.retrieval import energy_fit, filter_songs, parse_request  # noqa: F401


def looks_like_shell_command(user_input: str) -> bool:
    """Return True if the input looks like a terminal command, not a playlist query."""
    commands = (
        "python ", "python3 ", "pip ", "pip3 ",
        "ollama ", "brew ", "npm ", "git ", "yt-dlp ",
    )
    return user_input.strip().lower().startswith(commands)


def _offer_download(song_names: list[str]) -> None:
    """Prompt the user and download a list of songs as MP3."""
    choice = input(f"Download these {len(song_names)} matched songs as MP3? (y/n): ").strip().lower()
    if choice == "y":
        from src.download_songs import download_songs

        download_songs(song_names)


def main(enable_live_search: bool = False) -> int:
    """Run the interactive ShaadiSetlist REPL."""
    print("ShaadiSetlist AI  (type 'exit' to quit)\n")
    print("Format: event, mood[, region][, crowd]   e.g. sangeet, high energy, punjabi, gen-z")
    print("Also works without commas: shaadi slow\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            break

        if looks_like_shell_command(user_input):
            print("That looks like a terminal command. Type `exit`, run it in your shell, then start the app again.\n")
            continue

        result = generate_playlist_result(user_input, enable_live_search=enable_live_search)
        if result.request:
            print(f"\n{format_song_list(result.matched_songs)}\n")

        print(f"AI Playlist:\n{result.playlist}\n")

        if result.verified_songs:
            print(f"Found {len(result.verified_songs)} downloadable songs in the playlist:")
            for index, name in enumerate(result.verified_songs, start=1):
                print(f"  {index}. {name}")
            _offer_download(result.verified_songs)

        print("-" * 60 + "\n")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the interactive ShaadiSetlist REPL.")
    parser.add_argument(
        "--enable-live-search",
        action="store_true",
        help="Enable live YouTube search fallback when no dataset matches are found.",
    )
    args = parser.parse_args()
    raise SystemExit(main(enable_live_search=args.enable_live_search))
