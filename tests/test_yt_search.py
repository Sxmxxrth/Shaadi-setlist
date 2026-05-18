"""Tests for the live YouTube search fallback."""

from types import SimpleNamespace

import pytest

from src import yt_search


def test_build_search_query():
    query = yt_search.build_search_query("baraat", "hype", region="punjabi", crowd="gen-z")
    assert "baraat" in query
    assert "hype" in query
    assert "punjabi" in query
    assert "gen-z" in query
    assert query.endswith("wedding song")


def test_build_live_song_entries_uses_yt_dlp(monkeypatch):
    class DummyYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def extract_info(self, query, download):
            assert query.startswith("ytsearch2:")
            return {"entries": [{"title": "Live Song 1"}, {"title": "Live Song 2"}]}

    monkeypatch.setattr(yt_search, "yt_dlp", SimpleNamespace(YoutubeDL=DummyYDL))
    songs = yt_search.build_live_song_entries("haldi", "fun", region="north indian", crowd="family", limit=2)

    assert len(songs) == 2
    assert songs[0]["song"] == "Live Song 1"
    assert songs[0]["genre"] == "live search"
    assert songs[1]["event"] == "live search"
