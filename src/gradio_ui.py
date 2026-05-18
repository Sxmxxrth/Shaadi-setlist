"""
gradio_ui — Browser interface for ShaadiSetlist.
"""

from __future__ import annotations

import gradio as gr

from src.mashup_planner import build_mashup_plan, format_plan
from src.playlist import format_song_list
from src.playlist_service import PlaylistResult, generate_playlist_result


THEME = gr.themes.Soft(primary_hue="rose", secondary_hue="amber")
CUSTOM_CSS = """
.shaadi-title h1 { margin-bottom: 0.15rem; }
.shaadi-title p { margin-top: 0; color: #5f6368; }
textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
"""

EXAMPLES = [
    ["sangeet, high energy, punjabi, gen-z"],
    ["haldi, fun, family"],
    ["baraat, hype, punjabi"],
    ["bidaai, emotional, family"],
    ["cocktail, classy, gen-z"],
]


def _request_to_text(result: PlaylistResult) -> str:
    """Render the parsed request in a small human-readable block."""
    if not result.request:
        return "Invalid request"
    request = result.request
    return "\n".join(
        [
            f"Event: {request['event']}",
            f"Mood: {request['mood']}",
            f"Region: {request['region'] or 'not specified'}",
            f"Crowd: {request['crowd'] or 'mixed'}",
        ]
    )


def _verified_to_text(song_names: list[str]) -> str:
    if not song_names:
        return "No verified downloadable songs yet."
    return "\n".join(f"- {song}" for song in song_names)


def curate_playlist(user_input: str, enable_live_search: bool = False) -> tuple[str, str, str, str, str]:
    """Generate a playlist and format all UI outputs."""
    result = generate_playlist_result(user_input, enable_live_search=enable_live_search)
    status = result.error or "Ready"
    return (
        status,
        _request_to_text(result),
        format_song_list(result.matched_songs),
        result.playlist,
        _verified_to_text(result.verified_songs),
    )


def download_action(verified_text: str) -> str:
    """Download only verified song titles listed by the service layer."""
    from src.download_songs import download_songs

    songs = [line[2:].strip() for line in verified_text.splitlines() if line.startswith("- ")]
    if not songs:
        return "No verified songs to download."

    try:
        download_songs(songs)
    except Exception as exc:
        return f"Download failed: {exc}"
    return "Download completed. Check the downloads directory."


def plan_mashup(user_input: str, length: int) -> str:
    """Build a DJ-ready mashup plan for the UI."""
    try:
        plan = build_mashup_plan(user_input, length=int(length))
    except ValueError:
        return "Please enter at least an event and mood, for example: baraat, hype, punjabi"
    return format_plan(plan)


def build_ui() -> gr.Blocks:
    """Create the Gradio Blocks app."""
    with gr.Blocks(title="ShaadiSetlist") as demo:
        gr.Markdown(
            """
            # ShaadiSetlist
            AI-assisted Indian wedding playlist curator.
            """,
            elem_classes=["shaadi-title"],
        )

        with gr.Tab("Playlist Curator"):
            with gr.Row():
                request_box = gr.Textbox(
                    label="Wedding request",
                    placeholder="Example: sangeet, high energy, punjabi, gen-z",
                    value="sangeet, high energy, punjabi, gen-z",
                    lines=1,
                    scale=4,
                )
                live_search = gr.Checkbox(
                    label="Enable live YouTube fallback",
                    value=False,
                    scale=1,
                )

            generate_button = gr.Button("Generate Playlist", variant="primary")
            status_output = gr.Textbox(label="Status", lines=1)

            with gr.Row():
                parsed_output = gr.Textbox(label="Parsed request", lines=4)
                matched_output = gr.Textbox(label="Matched dataset/RAG songs", lines=12)

            playlist_output = gr.Textbox(label="AI playlist", lines=18)

            with gr.Row():
                verified_output = gr.Textbox(label="Verified downloadable songs", lines=6, scale=3)
                with gr.Column(scale=1):
                    download_button = gr.Button("Download MP3s", variant="secondary")
                    download_status = gr.Markdown()

            gr.Examples(
                examples=EXAMPLES,
                inputs=[request_box],
                label="Try an example",
            )

            generate_button.click(
                curate_playlist,
                inputs=[request_box, live_search],
                outputs=[status_output, parsed_output, matched_output, playlist_output, verified_output],
            )

            download_button.click(
                download_action,
                inputs=[verified_output],
                outputs=[download_status],
            )

        with gr.Tab("Mashup Planner"):
            with gr.Row():
                mashup_request = gr.Textbox(
                    label="Mashup request",
                    placeholder="Example: baraat, hype, punjabi, gen-z",
                    value="baraat, hype, punjabi, gen-z",
                    lines=1,
                    scale=4,
                )
                mashup_length = gr.Slider(
                    label="Number of songs",
                    minimum=3,
                    maximum=15,
                    value=8,
                    step=1,
                    scale=1,
                )

            mashup_button = gr.Button("Create Mashup Plan", variant="primary")
            mashup_output = gr.Textbox(label="DJ flow and transitions", lines=22)

            mashup_button.click(
                plan_mashup,
                inputs=[mashup_request, mashup_length],
                outputs=[mashup_output],
            )

    return demo


def main() -> None:
    """Launch the Gradio app."""
    build_ui().launch(theme=THEME, css=CUSTOM_CSS)


if __name__ == "__main__":
    main()
