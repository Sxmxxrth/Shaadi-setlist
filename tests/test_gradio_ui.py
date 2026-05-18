"""Tests for Gradio callback functions without launching a browser."""

from src import gradio_ui
from src.playlist_service import PlaylistResult


def test_curate_playlist_callback(monkeypatch):
    fake_result = PlaylistResult(
        request={"event": "sangeet", "mood": "high energy", "region": None, "crowd": None},
        matched_songs=[{"song": "Gallan Goodiyaan", "event": "sangeet", "mood": "high energy", "genre": "Bollywood", "energy": 9}],
        playlist="1. Gallan Goodiyaan",
        verified_songs=["Gallan Goodiyaan"],
    )
    monkeypatch.setattr(gradio_ui, "generate_playlist_result", lambda user_input, enable_live_search=False: fake_result)

    status, parsed, matched, playlist, verified = gradio_ui.curate_playlist("sangeet, hype")

    assert status == "Ready"
    assert "Event: sangeet" in parsed
    assert "Gallan Goodiyaan" in matched
    assert playlist == "1. Gallan Goodiyaan"
    assert "- Gallan Goodiyaan" in verified


def test_download_action_requires_verified_songs():
    assert gradio_ui.download_action("No verified downloadable songs yet.") == "No verified songs to download."
