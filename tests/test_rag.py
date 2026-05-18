"""Tests for lightweight local RAG helpers."""

from src import rag
from src.retrieval import filter_songs, parse_request


def test_rag_search_dataset_finds_metadata_match():
    results = rag.search_dataset("stylish groom squad procession", limit=5)
    titles = [song["song"] for song in results]

    assert "Tareefan" in titles


def test_rag_preserves_retrieval_expectations():
    request = parse_request("baraat, hype, punjabi, gen-z")
    songs = filter_songs(
        request["event"],
        request["mood"],
        region=request["region"],
        crowd=request["crowd"],
    )
    titles = {song["song"] for song in songs[:10]}

    assert titles & {"Mundian To Bach Ke", "Shera Di Kaum", "Mauja Hi Mauja", "Oh Ho Ho Ho"}
