"""Tests for the song retrieval pipeline."""

import json
from pathlib import Path

import pytest

from src.retrieval import filter_songs, parse_request

BASE_DIR = Path(__file__).resolve().parent


def normalize_title(title: str) -> str:
    return " ".join(title.strip().lower().split())


def load_cases():
    with open(BASE_DIR / "eval_cases.json") as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c["name"])
def test_retrieval(case):
    request = parse_request(case["input"])
    top_n = case.get("top_n", 10)
    matched = filter_songs(
        request["event"],
        request["mood"],
        region=request["region"],
        crowd=request["crowd"],
    )[:top_n]

    actual_titles = [song["song"] for song in matched]
    actual = {normalize_title(title) for title in actual_titles}
    expected = {normalize_title(title) for title in case.get("expected_any", [])}
    hits = expected & actual

    assert hits, f"Expected any of {case.get('expected_any')}, but got top matches: {actual_titles}"
