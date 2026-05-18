"""Tests for the shared playlist service."""

from src import playlist_service


def test_extract_verified_songs_cleans_and_deduplicates():
    reply = """
1. **Song Name: Gallan Goodiyaan** - warmup
2. Kala Chashma (peak moment)
3. Imaginary Wedding Anthem
4. Gallan Goodiyaan
"""

    assert playlist_service.extract_verified_songs(reply) == [
        "Gallan Goodiyaan",
        "Kala Chashma",
    ]


def test_generate_playlist_result_success(monkeypatch):
    def fake_generate(prompt):
        assert "Available songs from the dataset" in prompt
        return "1. Gallan Goodiyaan\nReason: Works well."

    monkeypatch.setattr(playlist_service, "generate_playlist", fake_generate)

    result = playlist_service.generate_playlist_result("sangeet, high energy, bollywood")

    assert result.ok
    assert result.request["event"] == "sangeet"
    assert result.matched_songs
    assert result.verified_songs == ["Gallan Goodiyaan"]


def test_generate_playlist_result_ollama_failure(monkeypatch):
    def fake_generate(prompt):
        raise RuntimeError("Ollama unavailable")

    monkeypatch.setattr(playlist_service, "generate_playlist", fake_generate)

    result = playlist_service.generate_playlist_result("haldi, fun, family")

    assert not result.ok
    assert "AI playlist unavailable" in result.playlist
    assert result.verified_songs


def test_generate_playlist_result_bad_input():
    result = playlist_service.generate_playlist_result("haldi")

    assert not result.ok
    assert result.request is None
    assert "Format:" in result.playlist
