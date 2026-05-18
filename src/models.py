"""
models — Shared type definitions for the song dataset.
"""

from typing import TypedDict


class Song(TypedDict, total=False):
    """Schema for a single song entry in dataset.json."""

    song: str
    event: str
    mood: str
    region: str
    language: str
    genre: str
    crowd: str
    energy: float | int
    bpm: str | int | float
    moment: str
    notes: str
    danceability: float | int
